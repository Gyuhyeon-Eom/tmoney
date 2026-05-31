"""
외부 데이터 수집 - API 키 필요
1. 기상청 ASOS 일별 기상관측 (2018~2026)
2. 기상청 ASOS 시간별 기상관측 (2018~2026)
"""
import csv
import os
import json
import time
from datetime import date, timedelta, datetime
from urllib.request import urlopen, Request
from urllib.parse import quote

API_KEY_RAW = "rIZ7FB29NjENK43w6dtqGHHqgMW1296UI442F4yT09cWOKYLx6D/mZVHI5+7UeDW3Id2iTwQWwVhrnSyhHrnYA=="
API_KEY = quote(API_KEY_RAW, safe='')  # URL 인코딩 필수 (+/= 등 특수문자)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "external_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_json(url, retries=3):
    """URL에서 JSON 데이터 가져오기"""
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            response = urlopen(req, timeout=30)
            content = response.read().decode("utf-8")
            return json.loads(content)
        except Exception as e:
            print(f"  [재시도 {attempt+1}/{retries}] {e}")
            time.sleep(2)
    return None


# ============================================================
# 1. 기상청 ASOS 일별 관측 (서울, 108)
# ============================================================
def collect_asos_daily():
    """기상청 ASOS 일별 관측 데이터 수집 (2018~2026)"""
    # API: 기상청_지상(종관,ASOS) 일자료 조회서비스
    # 한번에 최대 999일 요청 가능
    base_url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    stn_id = "108"  # 서울
    
    all_rows = []
    start = date(2018, 1, 1)
    end = date(2026, 5, 30)  # 전일까지
    
    current_start = start
    while current_start < end:
        current_end = min(current_start + timedelta(days=364), end)
        
        url = (
            f"{base_url}?"
            f"serviceKey={API_KEY}"
            f"&numOfRows=999"
            f"&pageNo=1"
            f"&dataType=JSON"
            f"&dataCd=ASOS"
            f"&dateCd=DAY"
            f"&startDt={current_start.strftime('%Y%m%d')}"
            f"&endDt={current_end.strftime('%Y%m%d')}"
            f"&stnIds={stn_id}"
        )
        
        print(f"  ASOS 일별: {current_start} ~ {current_end} 요청 중...")
        data = fetch_json(url)
        
        if data and "response" in data:
            body = data["response"].get("body", {})
            items = body.get("items", {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            
            for item in items:
                all_rows.append({
                    "date": item.get("tm", ""),
                    "avg_temp": item.get("avgTa", ""),        # 평균기온
                    "min_temp": item.get("minTa", ""),        # 최저기온
                    "max_temp": item.get("maxTa", ""),        # 최고기온
                    "rainfall": item.get("sumRn", ""),        # 일강수량
                    "avg_wind_speed": item.get("avgWs", ""),  # 평균풍속
                    "max_wind_speed": item.get("maxWs", ""),  # 최대풍속
                    "avg_humidity": item.get("avgRhm", ""),   # 평균상대습도
                    "sunshine_hours": item.get("sumSsHr", ""),# 합계일조시간
                    "snow_depth": item.get("ddMes", ""),      # 적설깊이
                    "avg_cloud": item.get("avgTca", ""),      # 평균전운량
                })
            
            print(f"    -> {len(items)}건 수집")
        else:
            result_code = "?"
            result_msg = "?"
            if data and "response" in data:
                header = data["response"].get("header", {})
                result_code = header.get("resultCode", "?")
                result_msg = header.get("resultMsg", "?")
            print(f"    -> 실패 (code={result_code}, msg={result_msg})")
            if data:
                print(f"    -> 응답: {json.dumps(data, ensure_ascii=False)[:300]}")
        
        current_start = current_end + timedelta(days=1)
        time.sleep(0.5)  # API 호출 간격
    
    if all_rows:
        path = os.path.join(OUTPUT_DIR, "weather_asos_daily_seoul_2018_2026.csv")
        fieldnames = ["date", "avg_temp", "min_temp", "max_temp", "rainfall",
                      "avg_wind_speed", "max_wind_speed", "avg_humidity",
                      "sunshine_hours", "snow_depth", "avg_cloud"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)
        print(f"[OK] ASOS 일별: {path} ({len(all_rows)}건)")
    else:
        print("[FAIL] ASOS 일별 데이터 수집 실패")


# ============================================================
# 2. 기상청 ASOS 시간별 관측 (서울, 108)
# ============================================================
def collect_asos_hourly():
    """기상청 ASOS 시간별 관측 데이터 수집 (2018~2026)"""
    base_url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    stn_id = "108"
    
    all_rows = []
    start = date(2018, 1, 1)
    end = date(2026, 5, 30)
    
    # 시간별은 한번에 최대 31일
    current_start = start
    batch = 0
    total_batches = ((end - start).days // 30) + 1
    
    while current_start < end:
        current_end = min(current_start + timedelta(days=30), end)
        batch += 1
        
        url = (
            f"{base_url}?"
            f"serviceKey={API_KEY}"
            f"&numOfRows=999"
            f"&pageNo=1"
            f"&dataType=JSON"
            f"&dataCd=ASOS"
            f"&dateCd=HR"
            f"&startDt={current_start.strftime('%Y%m%d')}"
            f"&endDt={current_end.strftime('%Y%m%d')}"
            f"&startHh=00"
            f"&endHh=23"
            f"&stnIds={stn_id}"
        )
        
        if batch % 10 == 1 or batch == 1:
            print(f"  ASOS 시간별: batch {batch}/{total_batches} ({current_start} ~ {current_end})...")
        
        data = fetch_json(url)
        
        if data and "response" in data:
            body = data["response"].get("body", {})
            items = body.get("items", {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            
            for item in items:
                tm = item.get("tm", "")  # "2018-01-01 00:00"
                dt_part = tm[:10] if len(tm) >= 10 else ""
                hr_part = tm[11:13] if len(tm) >= 13 else ""
                
                all_rows.append({
                    "datetime": tm,
                    "date": dt_part,
                    "hour": hr_part,
                    "temp": item.get("ta", ""),          # 기온
                    "rainfall": item.get("rn", ""),      # 강수량
                    "wind_speed": item.get("ws", ""),    # 풍속
                    "wind_dir": item.get("wd", ""),      # 풍향
                    "humidity": item.get("hm", ""),      # 습도
                    "pressure": item.get("pa", ""),      # 기압
                    "cloud": item.get("dc10TCA", ""),    # 전운량
                })
        else:
            if batch <= 3:  # 처음 몇개만 에러 출력
                result_code = "?"
                if data and "response" in data:
                    header = data["response"].get("header", {})
                    result_code = header.get("resultCode", "?")
                    result_msg = header.get("resultMsg", "?")
                    print(f"    -> 실패 (code={result_code}, msg={result_msg})")
                else:
                    print(f"    -> 응답 없음: {str(data)[:200]}")
        
        current_start = current_end + timedelta(days=1)
        time.sleep(0.3)  # API rate limit
    
    if all_rows:
        path = os.path.join(OUTPUT_DIR, "weather_asos_hourly_seoul_2018_2026.csv")
        fieldnames = ["datetime", "date", "hour", "temp", "rainfall", 
                      "wind_speed", "wind_dir", "humidity", "pressure", "cloud"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)
        print(f"[OK] ASOS 시간별: {path} ({len(all_rows)}건)")
    else:
        print("[FAIL] ASOS 시간별 데이터 수집 실패")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("기상 데이터 수집 시작 (data.go.kr API)")
    print("=" * 60)
    
    print("\n[1/2] ASOS 일별 관측 (서울)...")
    collect_asos_daily()
    
    print("\n[2/2] ASOS 시간별 관측 (서울)... (약 100 batch, 시간 좀 걸림)")
    collect_asos_hourly()
    
    print("\n" + "=" * 60)
    print("수집 완료! external_data/ 파일 목록:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        fpath = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(fpath)
        print(f"  {f}: {size:,} bytes")
    print("=" * 60)
