# 외부 데이터 명세서 (External Data Dictionary)

> 택시 시계열 추이 분석을 위한 외부 데이터 테이블 명세
> 수집일: 2026-05-31 | 기간: 2018-01-01 ~ 2026-05-31

---

## 1. calendar_2018_2026.csv

| 항목 | 내용 |
|------|------|
| 설명 | 일별 캘린더 (요일, 공휴일, 비영업일 플래그) |
| 행수 | 3,073건 |
| 기간 | 2018-01-01 ~ 2026-05-31 |
| 출처 | Python holidays 라이브러리 (한국 공휴일) |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 날짜 (YYYY-MM-DD) | 2018-01-01 |
| year | int | 연도 | 2018 |
| month | int | 월 | 1 |
| day | int | 일 | 1 |
| day_of_week | int | 요일 (0=월~6=일) | 0 |
| day_name | string | 요일 영문명 | Monday |
| is_weekend | int | 주말 여부 (0/1) | 0 |
| is_holiday | int | 공휴일 여부 (0/1) | 1 |
| holiday_name | string | 공휴일명 (없으면 빈값) | 신정연휴 |
| is_non_working | int | 비영업일 (주말 또는 공휴일) | 1 |

---

## 2. holidays_2018_2026.csv

| 항목 | 내용 |
|------|------|
| 설명 | 공휴일 목록 (공휴일만 추출) |
| 행수 | 166건 |
| 기간 | 2018 ~ 2026 |
| 출처 | Python holidays 라이브러리 |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 공휴일 날짜 (YYYY-MM-DD) | 2018-01-01 |
| holiday_name | string | 공휴일명 | 신정연휴 |
| day_of_week | string | 요일 영문명 | Monday |
| is_weekend | int | 주말 여부 (0/1) | 0 |

---

## 3. covid_korea_2018_2026.csv

| 항목 | 내용 |
|------|------|
| 설명 | 한국 코로나19 일별 확진자 수 |
| 행수 | 1,674건 |
| 기간 | 2020-01-05 ~ 2024-08-04 |
| 출처 | Our World in Data (GitHub) |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 날짜 (YYYY-MM-DD) | 2020-03-01 |
| new_cases | int | 일별 신규 확진자 수 | 586 |
| cumulative_cases | int | 누적 확진자 수 | 3736 |
| social_distancing_level | float | 거리두기 단계 (대략) | 2.0 |

---

## 4. social_distancing_daily.csv

| 항목 | 내용 |
|------|------|
| 설명 | 사회적 거리두기 단계 일별 매핑 |
| 행수 | 3,073건 |
| 기간 | 2018-01-01 ~ 2026-05-31 |
| 출처 | 수동 정리 (정부 발표 기준) |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 날짜 (YYYY-MM-DD) | 2021-07-12 |
| distancing_level | float | 거리두기 단계 (0/1/1.5/2/2.5/4) | 4.0 |
| distancing_desc | string | 단계 설명 | 수도권 4단계 |

### 거리두기 단계 변천

| 기간 | 단계 | 설명 |
|------|------|------|
| ~2020-03-21 | 0 | 코로나 이전 |
| 2020-03-22 ~ 2020-06-27 | 1 | 사회적 거리두기 1단계 |
| 2020-06-28 ~ 2020-08-29 | 1.5 | 수도권 강화 |
| 2020-08-30 ~ 2020-10-11 | 2 | 수도권 2단계 |
| 2020-10-12 ~ 2020-11-23 | 1 | 1단계 완화 |
| 2020-11-24 ~ 2020-12-07 | 2 | 수도권 2단계 |
| 2020-12-08 ~ 2021-02-14 | 2.5 | 수도권 2.5단계 |
| 2021-02-15 ~ 2021-07-11 | 2 | 2단계 유지 |
| 2021-07-12 ~ 2021-10-31 | 4 | 수도권 4단계 |
| 2021-11-01 ~ 2021-12-17 | 0 | 위드코로나 |
| 2021-12-18 ~ 2022-04-17 | 4 | 거리두기 재강화 |
| 2022-04-18 ~ | 0 | 전면 해제 |

---

## 5. taxi_events_timeline.csv

| 항목 | 내용 |
|------|------|
| 설명 | 택시 시장 주요 이벤트 타임라인 |
| 행수 | 22건 |
| 기간 | 2018 ~ 2024 |
| 출처 | 뉴스/정부 발표 기반 수동 정리 |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 이벤트 날짜 (YYYY-MM-DD) | 2018-10-01 |
| event | string | 이벤트명 | 택시요금인상 |
| category | string | 분류 (policy/platform/covid) | policy |
| description | string | 상세 설명 | 서울 택시 기본요금 3000->3800원 인상 |

### 카테고리별 이벤트 수
- policy: 택시 요금 인상, 심야할증 변경 등 (3건)
- platform: 카카오T, 타다 관련 (4건)
- covid: 코로나 관련 거리두기/해제 (15건)

---

## 6. weather_asos_daily_seoul_2018_2026.csv

| 항목 | 내용 |
|------|------|
| 설명 | 서울(108) ASOS 일별 기상관측 |
| 행수 | 3,072건 |
| 기간 | 2018-01-01 ~ 2026-05-30 |
| 출처 | 기상청 공공데이터포털 API (지상 종관 ASOS 일자료) |

| 컬럼명 | 타입 | 단위 | 설명 | 예시 |
|--------|------|------|------|------|
| date | string | - | 날짜 (YYYY-MM-DD) | 2018-01-01 |
| avg_temp | float | C | 일 평균기온 | -1.3 |
| min_temp | float | C | 일 최저기온 | -5.1 |
| max_temp | float | C | 일 최고기온 | 3.8 |
| rainfall | float | mm | 일 강수량 (없으면 빈값) | 12.5 |
| avg_wind_speed | float | m/s | 일 평균풍속 | 1.4 |
| max_wind_speed | float | m/s | 일 최대풍속 | 3.8 |
| avg_humidity | float | % | 일 평균상대습도 | 39.1 |
| sunshine_hours | float | hr | 일 합계일조시간 | 8.3 |
| snow_depth | float | cm | 적설깊이 (없으면 빈값) | 5.0 |
| avg_cloud | float | 할 | 일 평균전운량 (0~10) | 1.0 |

### 파생 가능 변수
- `is_rainy`: rainfall > 0
- `is_heavy_rain`: rainfall >= 30
- `is_snow`: snow_depth > 0
- `temp_category`: 혹한(<-10), 추위(-10~0), 서늘(0~10), 쾌적(10~25), 더움(25~30), 폭염(>30)

---

## 7. weather_asos_hourly_seoul_2018_2026.csv

| 항목 | 내용 |
|------|------|
| 설명 | 서울(108) ASOS 시간별 기상관측 |
| 행수 | 73,728건 |
| 기간 | 2018-01-01 00:00 ~ 2026-05-30 23:00 |
| 출처 | 기상청 공공데이터포털 API (지상 종관 ASOS 시간자료) |

| 컬럼명 | 타입 | 단위 | 설명 | 예시 |
|--------|------|------|------|------|
| datetime | string | - | 관측시각 (YYYY-MM-DD HH:MM) | 2018-01-01 00:00 |
| date | string | - | 날짜 (YYYY-MM-DD) | 2018-01-01 |
| hour | string | - | 시간 (00~23) | 00 |
| temp | float | C | 기온 | -3.2 |
| rainfall | float | mm | 강수량 (없으면 빈값) | 0.5 |
| wind_speed | float | m/s | 풍속 | 0.5 |
| wind_dir | int | 도 | 풍향 (0~360) | 110 |
| humidity | float | % | 상대습도 | 40 |
| pressure | float | hPa | 기압 | 1015.4 |
| cloud | int | 할 | 전운량 (0~10, 빈값 있음) | 3 |

---

## 8. subway_ridership_2024.csv

| 항목 | 내용 |
|------|------|
| 설명 | 서울교통공사 역별 일별 시간대별 승하차인원 |
| 행수 | 199,424건 |
| 기간 | 2024-01-01 ~ 2024-12-31 |
| 출처 | 공공데이터포털 (서울교통공사) |
| 인코딩 | UTF-8 (원본 EUC-KR에서 변환) |

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| 연번 | int | 순번 | 1 |
| 수송일자 | string | 날짜 (YYYY-MM-DD) | 2024-01-01 |
| 호선 | string | 지하철 호선 | 1호선 |
| 역번호 | int | 역 고유번호 | 150 |
| 역명 | string | 역 이름 | 서울역 |
| 승하차구분 | string | 승차/하차 | 승차 |
| 06시이전 | int | 06시 이전 인원 | 383 |
| 06-07시간대 | int | 06~07시 인원 | 257 |
| 07-08시간대 | int | 07~08시 인원 | 308 |
| ... | int | (시간대별 동일) | ... |
| 23-24시간대 | int | 23~24시 인원 | 868 |
| 24시이후 | int | 24시 이후 인원 | 43 |

### 포함 호선
- 1~8호선 (서울교통공사 관할 구간만)
- 1호선: 서울역~청량리
- 4호선: 남태령 이전까지
- 8호선: 암사역사공원역까지

---

## 테이블 관계도

```
택시 데이터 (DC_TBYXD012.csv)
    |
    +-- JOIN on date --> calendar (요일/공휴일)
    +-- JOIN on date --> weather_daily (일별 기상)
    +-- JOIN on date+hour --> weather_hourly (시간별 기상)
    +-- JOIN on date --> covid (코로나 확진자)
    +-- JOIN on date --> social_distancing (거리두기 단계)
    +-- LOOKUP on date --> taxi_events (이벤트 매칭)
    +-- JOIN on date+hour --> subway (지하철 승하차, 2024만)
```

---

## 분석 노트북 매핑

| 노트북 | 사용 외부 데이터 |
|--------|-----------------|
| 14_multi_period_decomposition | calendar, weather_daily |
| 15_causal_impact | calendar, weather_daily, covid, social_distancing, taxi_events |
| 16_change_point_detection | calendar, covid, social_distancing, taxi_events |
| 17_weather_elasticity | weather_daily, weather_hourly, calendar |
| 18_subway_substitution | subway, weather_daily, calendar |
| 19_explainable_anomaly | weather_daily, covid, social_distancing, taxi_events, calendar |
