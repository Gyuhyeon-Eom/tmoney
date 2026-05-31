"""
외부 데이터 수집 스크립트 (API 키 불필요한 것들)
- 공휴일/특수일 (2018~2026)
- 코로나19 일별 확진자 (공개 CSV)
- 택시 요금 인상/플랫폼 이벤트 타임라인
"""
import csv
import os
import json
from datetime import date, timedelta, datetime
from urllib.request import urlopen, Request

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "external_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. 공휴일 + 특수일 (2018~2026)
# ============================================================
def generate_holidays():
    """Python holidays 라이브러리 또는 수동 정의로 공휴일 CSV 생성"""
    try:
        import holidays
        kr_holidays = holidays.KR(years=range(2018, 2027))
        rows = []
        for dt, name in sorted(kr_holidays.items()):
            rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "holiday_name": name,
                "day_of_week": dt.strftime("%A"),
                "is_weekend": 1 if dt.weekday() >= 5 else 0,
            })
    except ImportError:
        # holidays 라이브러리 없으면 수동 정의 (주요 공휴일만)
        print("holidays 라이브러리 없음, 수동 정의로 생성")
        rows = []
        # 고정 공휴일
        fixed = [
            ("01-01", "신정"),
            ("03-01", "삼일절"),
            ("05-05", "어린이날"),
            ("06-06", "현충일"),
            ("08-15", "광복절"),
            ("10-03", "개천절"),
            ("10-09", "한글날"),
            ("12-25", "크리스마스"),
        ]
        # 음력 공휴일 (대략적 양력 변환 - 년도별)
        lunar = {
            2018: [("02-15","02-16","02-17","설날"),("09-23","09-24","09-25","추석"),("05-22","석가탄신일")],
            2019: [("02-04","02-05","02-06","설날"),("09-12","09-13","09-14","추석"),("05-12","석가탄신일")],
            2020: [("01-24","01-25","01-26","설날"),("09-30","10-01","10-02","추석"),("04-30","석가탄신일")],
            2021: [("02-11","02-12","02-13","설날"),("09-20","09-21","09-22","추석"),("05-19","석가탄신일")],
            2022: [("01-31","02-01","02-02","설날"),("09-09","09-10","09-11","추석"),("05-08","석가탄신일")],
            2023: [("01-21","01-22","01-23","설날"),("09-28","09-29","09-30","추석"),("05-27","석가탄신일")],
            2024: [("02-09","02-10","02-11","설날"),("09-16","09-17","09-18","추석"),("05-15","석가탄신일")],
            2025: [("01-28","01-29","01-30","설날"),("10-05","10-06","10-07","추석"),("05-05","석가탄신일")],
            2026: [("02-16","02-17","02-18","설날"),("09-24","09-25","09-26","추석"),("05-24","석가탄신일")],
        }
        for year in range(2018, 2027):
            for md, name in fixed:
                dt = date(year, int(md[:2]), int(md[3:]))
                rows.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "holiday_name": name,
                    "day_of_week": dt.strftime("%A"),
                    "is_weekend": 1 if dt.weekday() >= 5 else 0,
                })
            if year in lunar:
                for item in lunar[year]:
                    name = item[-1]
                    dates = item[:-1]
                    for md in dates:
                        dt = date(year, int(md[:2]), int(md[3:]))
                        rows.append({
                            "date": dt.strftime("%Y-%m-%d"),
                            "holiday_name": name,
                            "day_of_week": dt.strftime("%A"),
                            "is_weekend": 1 if dt.weekday() >= 5 else 0,
                        })

    # 날짜 캘린더 (2018-01-01 ~ 2026-05-31) with 특수일 플래그
    calendar_rows = []
    holiday_dates = {r["date"]: r["holiday_name"] for r in rows}
    
    start = date(2018, 1, 1)
    end = date(2026, 5, 31)
    current = start
    while current <= end:
        ds = current.strftime("%Y-%m-%d")
        calendar_rows.append({
            "date": ds,
            "year": current.year,
            "month": current.month,
            "day": current.day,
            "day_of_week": current.weekday(),  # 0=Mon
            "day_name": current.strftime("%A"),
            "is_weekend": 1 if current.weekday() >= 5 else 0,
            "is_holiday": 1 if ds in holiday_dates else 0,
            "holiday_name": holiday_dates.get(ds, ""),
            "is_non_working": 1 if (current.weekday() >= 5 or ds in holiday_dates) else 0,
        })
        current += timedelta(days=1)
    
    # 공휴일 목록
    path1 = os.path.join(OUTPUT_DIR, "holidays_2018_2026.csv")
    with open(path1, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(sorted(rows, key=lambda x: x["date"]))
    print(f"[OK] 공휴일 목록: {path1} ({len(rows)}건)")
    
    # 날짜 캘린더
    path2 = os.path.join(OUTPUT_DIR, "calendar_2018_2026.csv")
    with open(path2, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=calendar_rows[0].keys())
        w.writeheader()
        w.writerows(calendar_rows)
    print(f"[OK] 날짜 캘린더: {path2} ({len(calendar_rows)}건)")


# ============================================================
# 2. 코로나19 일별 확진자 (Our World in Data - 공개)
# ============================================================
def collect_covid():
    """Our World in Data에서 한국 코로나 확진자 수집"""
    url = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/cases_deaths/new_cases.csv"
    print(f"코로나 데이터 다운로드 중... {url}")
    
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urlopen(req, timeout=30)
        content = response.read().decode("utf-8")
        
        import io
        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for row in reader:
            dt = row.get("date", "")
            if dt < "2018-01-01" or dt > "2026-05-31":
                continue
            kr_cases = row.get("South Korea", "")
            if kr_cases == "":
                kr_cases = "0"
            try:
                kr_cases_int = int(float(kr_cases))
            except:
                kr_cases_int = 0
            rows.append({
                "date": dt,
                "new_cases": kr_cases_int,
            })
        
        # 누적 계산
        cumulative = 0
        for r in rows:
            cumulative += r["new_cases"]
            r["cumulative_cases"] = cumulative
            # 거리두기 단계 대략 매핑
            if dt < "2020-03-01":
                r["social_distancing_level"] = 0
            elif dt < "2020-06-28":
                r["social_distancing_level"] = 1
            elif dt < "2020-11-24":
                r["social_distancing_level"] = 2  # 수도권 2단계
            elif dt < "2021-07-12":
                r["social_distancing_level"] = 2.5
            elif dt < "2022-04-18":
                r["social_distancing_level"] = 4  # 4단계
            else:
                r["social_distancing_level"] = 0  # 해제
        
        path = os.path.join(OUTPUT_DIR, "covid_korea_2018_2026.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "new_cases", "cumulative_cases", "social_distancing_level"])
            w.writeheader()
            w.writerows(rows)
        print(f"[OK] 코로나 데이터: {path} ({len(rows)}건)")
    except Exception as e:
        print(f"[FAIL] 코로나 데이터 수집 실패: {e}")
        # 빈 파일 생성
        path = os.path.join(OUTPUT_DIR, "covid_korea_2018_2026.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("date,new_cases,cumulative_cases,social_distancing_level\n")
        print("빈 파일 생성됨. 수동으로 채워야 함")


# ============================================================
# 3. 택시 관련 이벤트 타임라인
# ============================================================
def generate_events_timeline():
    """택시 시장에 영향을 준 주요 이벤트"""
    events = [
        {"date": "2018-10-01", "event": "택시요금인상", "category": "policy", "description": "서울 택시 기본요금 3000→3800원 인상"},
        {"date": "2018-10-08", "event": "카카오T택시_출시", "category": "platform", "description": "카카오T 택시 호출 서비스 정식 런칭(2017이나 본격화)"},
        {"date": "2019-02-21", "event": "타다_서비스개시", "category": "platform", "description": "VCNC 타다 렌터카 서비스 본격화"},
        {"date": "2019-10-28", "event": "타다_기소", "category": "platform", "description": "타다 불법 운송 혐의 기소"},
        {"date": "2020-01-20", "event": "코로나_첫확진", "category": "covid", "description": "한국 코로나19 첫 확진자 발생"},
        {"date": "2020-02-29", "event": "코로나_대구폭증", "category": "covid", "description": "대구 신천지 관련 확진자 폭증"},
        {"date": "2020-03-22", "event": "사회적거리두기_시작", "category": "covid", "description": "사회적 거리두기 시행"},
        {"date": "2020-04-06", "event": "타다금지법_통과", "category": "platform", "description": "여객자동차운수사업법 개정안(타다금지법) 국회 통과"},
        {"date": "2020-04-11", "event": "타다_서비스종료", "category": "platform", "description": "타다 베이직 서비스 종료"},
        {"date": "2020-08-30", "event": "거리두기_2단계", "category": "covid", "description": "수도권 사회적 거리두기 2단계"},
        {"date": "2020-12-08", "event": "거리두기_2.5단계", "category": "covid", "description": "수도권 2.5단계 격상"},
        {"date": "2021-07-12", "event": "거리두기_4단계", "category": "covid", "description": "수도권 사회적 거리두기 4단계"},
        {"date": "2021-11-01", "event": "위드코로나_시작", "category": "covid", "description": "단계적 일상회복 시행"},
        {"date": "2021-12-18", "event": "위드코로나_중단", "category": "covid", "description": "오미크론 확산으로 거리두기 재강화"},
        {"date": "2022-03-05", "event": "오미크론_피크", "category": "covid", "description": "일일 확진자 62만명 피크"},
        {"date": "2022-04-18", "event": "거리두기_해제", "category": "covid", "description": "사회적 거리두기 전면 해제"},
        {"date": "2022-06-01", "event": "마스크의무_완화", "category": "covid", "description": "실외 마스크 의무 해제"},
        {"date": "2023-01-30", "event": "실내마스크_해제", "category": "covid", "description": "실내 마스크 의무 해제 (의료기관 제외)"},
        {"date": "2023-02-01", "event": "택시요금인상", "category": "policy", "description": "서울 택시 기본요금 3800→4800원 인상"},
        {"date": "2023-05-11", "event": "코로나_위기단계_하향", "category": "covid", "description": "감염병 위기경보 '심각→경계' 하향"},
        {"date": "2023-06-01", "event": "코로나_4급감염병", "category": "covid", "description": "코로나19 4급 감염병으로 전환"},
        {"date": "2024-02-01", "event": "심야할증_확대", "category": "policy", "description": "심야할증 시간 22시→23시 변경, 할증률 조정"},
    ]
    
    path = os.path.join(OUTPUT_DIR, "taxi_events_timeline.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "event", "category", "description"])
        w.writeheader()
        w.writerows(events)
    print(f"[OK] 이벤트 타임라인: {path} ({len(events)}건)")


# ============================================================
# 4. 거리두기 단계 일별 매핑
# ============================================================
def generate_distancing_levels():
    """사회적 거리두기 단계 일별 CSV"""
    # (시작일, 종료일, 단계, 설명)
    periods = [
        ("2018-01-01", "2020-03-21", 0, "코로나 이전"),
        ("2020-03-22", "2020-06-27", 1, "사회적 거리두기 1단계"),
        ("2020-06-28", "2020-08-29", 1.5, "수도권 강화"),
        ("2020-08-30", "2020-10-11", 2, "수도권 2단계"),
        ("2020-10-12", "2020-11-23", 1, "1단계 완화"),
        ("2020-11-24", "2020-12-07", 2, "수도권 2단계"),
        ("2020-12-08", "2021-02-14", 2.5, "수도권 2.5단계"),
        ("2021-02-15", "2021-07-11", 2, "2단계 유지"),
        ("2021-07-12", "2021-10-31", 4, "수도권 4단계"),
        ("2021-11-01", "2021-12-17", 0, "위드코로나(단계적 일상회복)"),
        ("2021-12-18", "2022-04-17", 4, "거리두기 재강화"),
        ("2022-04-18", "2026-05-31", 0, "거리두기 전면 해제"),
    ]
    
    rows = []
    for start_s, end_s, level, desc in periods:
        start = datetime.strptime(start_s, "%Y-%m-%d").date()
        end = datetime.strptime(end_s, "%Y-%m-%d").date()
        current = start
        while current <= end:
            rows.append({
                "date": current.strftime("%Y-%m-%d"),
                "distancing_level": level,
                "distancing_desc": desc,
            })
            current += timedelta(days=1)
    
    path = os.path.join(OUTPUT_DIR, "social_distancing_daily.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "distancing_level", "distancing_desc"])
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] 거리두기 단계: {path} ({len(rows)}건)")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("외부 데이터 수집 시작")
    print("=" * 60)
    
    print("\n[1/4] 공휴일/캘린더 생성...")
    generate_holidays()
    
    print("\n[2/4] 코로나19 데이터 수집...")
    collect_covid()
    
    print("\n[3/4] 택시 이벤트 타임라인 생성...")
    generate_events_timeline()
    
    print("\n[4/4] 거리두기 단계 일별 매핑...")
    generate_distancing_levels()
    
    print("\n" + "=" * 60)
    print("수집 완료! 생성된 파일:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(fpath)
        print(f"  {f}: {size:,} bytes")
    print("=" * 60)
    print("\n[TODO] API 키 받으면 추가 수집할 데이터:")
    print("  - 기상청 ASOS 시간별 기상관측 (기온/강수/풍속/습도)")
    print("  - 서울 지하철 역별 시간대별 승하차인원")
    print("  - 에어코리아 미세먼지 시간별")
