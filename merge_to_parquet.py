#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
티머니 택시 데이터: 테이블별 분기 CSV -> Parquet 합치기
DBeaver에서 분기 단위로 export한 CSV들을 테이블별로 하나의 parquet로 결합.

전제 파일명 규칙 (다르면 아래 CONFIG만 수정):
  대용량: DC_TBYXS003_2018Q1.csv, DC_TBYXS003_2018Q2.csv, ...
  마스터: DC_TBYXM001.csv (분기 구분 없음)

대용량(수억 건) 대응: CSV를 통째로 읽지 않고 청크 단위로 읽어 parquet에 이어씀.
타입 충돌 방지: 모든 컬럼을 문자열로 읽음 (원본 보존, STAT_DT도 YYYYMMDD 문자열 유지).
"""

import sys
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ============================================
# CONFIG  -- 실제 환경과 다르면 여기만 수정
# ============================================
INPUT_DIR = Path("./csv")          # DBeaver로 뽑은 CSV들이 있는 폴더
OUTPUT_DIR = Path("./parquet")     # 합친 parquet 저장 폴더
DELIMITER = "|"                    # CSV 구분자
ENCODING = "utf-8"                # CSV 인코딩
CHUNK_ROWS = 200_000               # 한 번에 읽을 행 수 (메모리 사용량 조절)

# 합칠 테이블 목록
TABLES = [
    "DC_TBYXM001", "DC_TBYXM002", "DC_TBYXM036", "DC_TBYXM037",  # 마스터
    "DC_TBYXS002", "DC_TBYXS003", "DC_TBYXS004", "DC_TBYXS005",  # 대용량
]
# ============================================


def quarter_sort_key(path: Path):
    """파일명에서 연도/분기를 뽑아 정렬용 키 생성. 분기 없으면 (0,0)."""
    m = re.search(r"_(\d{4})Q(\d)", path.stem)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def find_files(table: str):
    """해당 테이블의 CSV 조각들을 분기 순서대로 반환."""
    # table_ 로 시작하는 분기 파일 + 정확히 table.csv (마스터) 둘 다 매칭
    files = [p for p in INPUT_DIR.glob(f"{table}*.csv")]
    files.sort(key=quarter_sort_key)
    return files


def merge_table(table: str):
    files = find_files(table)
    if not files:
        print(f"[SKIP] {table}: CSV 없음")
        return

    out_path = OUTPUT_DIR / f"{table}.parquet"
    writer = None
    total_rows = 0

    print(f"[START] {table}  ({len(files)}개 파일)")
    try:
        for f in files:
            file_rows = 0
            # 모든 컬럼 문자열(dtype=str)로 읽어 타입 충돌 방지
            reader = pd.read_csv(
                f,
                sep=DELIMITER,
                encoding=ENCODING,
                dtype=str,
                keep_default_na=False,  # 빈칸을 NaN 아닌 "" 로 (원본 보존)
                chunksize=CHUNK_ROWS,
            )
            for chunk in reader:
                tbl = pa.Table.from_pandas(chunk, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, tbl.schema, compression="snappy")
                else:
                    # 컬럼 구조 불일치 방어: 첫 파일 스키마에 맞춤
                    tbl = tbl.cast(writer.schema)
                writer.write_table(tbl)
                file_rows += len(chunk)
            total_rows += file_rows
            print(f"   + {f.name}: {file_rows:,} rows")
    finally:
        if writer is not None:
            writer.close()

    print(f"[DONE] {table}: 총 {total_rows:,} rows -> {out_path}")


def main():
    if not INPUT_DIR.exists():
        print(f"입력 폴더가 없습니다: {INPUT_DIR.resolve()}")
        sys.exit(1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for table in TABLES:
        merge_table(table)

    print("\n전체 완료.")


if __name__ == "__main__":
    main()
