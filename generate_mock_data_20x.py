#!/usr/bin/env python3
"""티머니 STIS 택시 데이터 13개 테이블 목데이터 생성 (20x scale, 2018-01 ~ 2026-04)"""

import os
import csv
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import string
import time

np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 공통 상수 & 유틸
# ============================================================
DATE_START = datetime(2018, 1, 1)
DATE_END = datetime(2026, 4, 30)
DATE_RANGE_DAYS = (DATE_END - DATE_START).days + 1
TOTAL_SECONDS = int((DATE_END - DATE_START).total_seconds())

def fmt_dt14(dt):
    return dt.strftime('%Y%m%d%H%M%S')

def fmt_dt8(dt):
    return dt.strftime('%Y%m%d')

# Vectorized date helpers
DATE_LIST_8 = [(DATE_START + timedelta(days=d)).strftime('%Y%m%d') for d in range(DATE_RANGE_DAYS)]

def random_dates8_vec(n):
    indices = np.random.randint(0, DATE_RANGE_DAYS, size=n)
    return [DATE_LIST_8[i] for i in indices]

HOUR_WEIGHTS = np.array([1]*6 + [3,5,5,3] + [2]*4 + [1]*2 + [3,5,5,3] + [2]*2 + [1]*2, dtype=float)
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

def random_datetimes_weighted_vec(n):
    """Vectorized weighted datetime generation"""
    days = np.random.randint(0, DATE_RANGE_DAYS, size=n)
    hours = np.random.choice(24, size=n, p=HOUR_WEIGHTS)
    minutes = np.random.randint(0, 60, size=n)
    seconds = np.random.randint(0, 60, size=n)
    # Return as total seconds from DATE_START for efficient processing
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total

def seconds_to_dt14(secs_array):
    """Convert array of seconds-from-start to dt14 strings"""
    base_ts = int(DATE_START.timestamp())
    results = []
    for s in secs_array:
        dt = datetime.fromtimestamp(base_ts + int(s))
        results.append(dt.strftime('%Y%m%d%H%M%S'))
    return results

def seconds_to_dt14_batch(secs_array):
    """Faster batch conversion"""
    base = DATE_START
    return [(base + timedelta(seconds=int(s))).strftime('%Y%m%d%H%M%S') for s in secs_array]

def seconds_to_dt8_batch(secs_array):
    base = DATE_START
    return [(base + timedelta(seconds=int(s))).strftime('%Y%m%d') for s in secs_array]

# ============================================================
# 서울 주요 거점 좌표 (WGS84)
# ============================================================
SEOUL_HOTSPOTS = {
    '강남역':     (127.0276, 37.4979),
    '홍대입구':   (126.9237, 37.5568),
    '서울역':     (126.9725, 37.5547),
    '잠실':       (127.1001, 37.5133),
    '여의도':     (126.9246, 37.5219),
    '신촌':       (126.9368, 37.5551),
    '건대입구':   (127.0582, 37.5405),
    '명동':       (126.9857, 37.5636),
    '이태원':     (126.9944, 37.5345),
    '압구정':     (127.0286, 37.5272),
    '삼성':       (127.0630, 37.5089),
    '역삼':       (127.0364, 37.5006),
    '신림':       (126.9290, 37.4843),
    '구로디지털': (126.9014, 37.4854),
    '송파':       (127.1058, 37.5048),
    '목동':       (126.8756, 37.5244),
    '노원':       (127.0617, 37.6554),
    '왕십리':     (127.0371, 37.5613),
    '동대문':     (127.0093, 37.5712),
    '종로3가':    (126.9920, 37.5710),
    '김포공항':   (126.8014, 37.5585),
    '인천공항':   (126.4407, 37.4602),
    '서울고속터미널': (127.0049, 37.5048),
    '동서울터미널':   (127.0947, 37.5347),
    '용산':       (126.9648, 37.5299),
    '수서역':     (127.1020, 37.4875),
    '청량리':     (127.0466, 37.5807),
    '합정':       (126.9139, 37.5496),
    '상봉':       (127.0856, 37.5960),
    '디지털미디어시티': (126.8996, 37.5770),
}
HOTSPOT_NAMES = list(SEOUL_HOTSPOTS.keys())
HOTSPOT_COORDS_X = np.array([c[0] for c in SEOUL_HOTSPOTS.values()])
HOTSPOT_COORDS_Y = np.array([c[1] for c in SEOUL_HOTSPOTS.values()])
NUM_HOTSPOTS = len(HOTSPOT_NAMES)

# OD 패턴
OD_PATTERNS = [
    ('강남역', '홍대입구', 5), ('서울역', '강남역', 5), ('잠실', '강남역', 4),
    ('여의도', '강남역', 4), ('서울역', '김포공항', 5), ('강남역', '서울고속터미널', 3),
    ('홍대입구', '이태원', 3), ('명동', '동대문', 3), ('건대입구', '잠실', 3),
    ('신촌', '여의도', 3), ('역삼', '서울역', 3), ('압구정', '삼성', 2),
    ('용산', '이태원', 2), ('수서역', '강남역', 3), ('청량리', '서울역', 2),
    ('송파', '잠실', 2), ('노원', '종로3가', 2), ('합정', '홍대입구', 2),
    ('동서울터미널', '강남역', 3), ('김포공항', '강남역', 4),
    ('강남역', '서울역', 4), ('홍대입구', '강남역', 4), ('강남역', '잠실', 3),
    ('강남역', '여의도', 3), ('이태원', '명동', 2),
]
OD_ORIGINS = [SEOUL_HOTSPOTS[o] for o, d, w in OD_PATTERNS]
OD_DESTS = [SEOUL_HOTSPOTS[d] for o, d, w in OD_PATTERNS]
OD_WEIGHTS = np.array([w for o, d, w in OD_PATTERNS], dtype=float)
OD_WEIGHTS /= OD_WEIGHTS.sum()
OD_ORIGIN_NAMES = [o for o, d, w in OD_PATTERNS]
OD_DEST_NAMES = [d for o, d, w in OD_PATTERNS]

def pick_od_vec(n):
    """Vectorized OD pair selection"""
    indices = np.random.choice(len(OD_PATTERNS), size=n, p=OD_WEIGHTS)
    ox = np.array([OD_ORIGINS[i][0] for i in indices]) + np.random.normal(0, 0.005, n)
    oy = np.array([OD_ORIGINS[i][1] for i in indices]) + np.random.normal(0, 0.003, n)
    dx = np.array([OD_DESTS[i][0] for i in indices]) + np.random.normal(0, 0.005, n)
    dy = np.array([OD_DESTS[i][1] for i in indices]) + np.random.normal(0, 0.003, n)
    o_names = [OD_ORIGIN_NAMES[i] for i in indices]
    d_names = [OD_DEST_NAMES[i] for i in indices]
    return o_names, np.round(ox, 6), np.round(oy, 6), d_names, np.round(dx, 6), np.round(dy, 6)

def coord_near_hotspot_vec(n):
    """Vectorized hotspot-near coordinate generation"""
    indices = np.random.randint(0, NUM_HOTSPOTS, size=n)
    x = HOTSPOT_COORDS_X[indices] + np.random.normal(0, 0.008, n)
    y = HOTSPOT_COORDS_Y[indices] + np.random.normal(0, 0.005, n)
    x = np.clip(np.round(x, 6), 126.8, 127.2)
    y = np.clip(np.round(y, 6), 37.4, 37.7)
    return x, y

# ============================================================
# 100x 마스터 데이터
# ============================================================
NUM_BIZR = 100000
NUM_VEHC = 400000
NUM_DRIVERS = 300000

print(f"Preparing master IDs: {NUM_BIZR} bizr, {NUM_VEHC} vehc, {NUM_DRIVERS} drivers...")

TRANSP_BIZR_IDS = [f'TB{i:08d}' for i in range(1, NUM_BIZR + 1)]
TAXI_VEHC_IDS = [f'V{i:012d}' for i in range(1, NUM_VEHC + 1)]
DRIVER_IDS = [f'D{i:05d}' for i in range(1, NUM_DRIVERS + 1)]
DRIVER_CERT_NOS = [f'DC{i:08d}' for i in range(1, NUM_DRIVERS + 1)]
DRIVER_CERT_MAP = dict(zip(DRIVER_IDS, DRIVER_CERT_NOS))

# Pre-compute vehicle-to-bizr mapping (vectorized assignment)
VEHC_BIZR_IDX = np.random.randint(0, NUM_BIZR, size=NUM_VEHC)
VEHC_BIZR_MAP = {TAXI_VEHC_IDS[i]: TRANSP_BIZR_IDS[VEHC_BIZR_IDX[i]] for i in range(NUM_VEHC)}

# Driver-to-vehicle mapping
DRIVER_VEHC_MAP = {DRIVER_IDS[i]: TAXI_VEHC_IDS[i % NUM_VEHC] for i in range(NUM_DRIVERS)}

# Numpy arrays for fast random selection
VEHC_IDS_ARR = np.arange(NUM_VEHC)
DRIVER_IDS_ARR = np.arange(NUM_DRIVERS)
BIZR_IDS_ARR = np.arange(NUM_BIZR)

# Business name generation for 5000
BASE_BIZR_NAMES = [
    '서울개인택시', '강남운수', '한성운수', '삼성교통', '서울교통',
    '대한운수', '동양교통', '국제운수', '신한운수', '중앙교통',
    '태평양운수', '아시아교통', '한국운수', '동서교통', '남북운수',
    '금성교통', '우리교통', '대성운수', '미래운수', '서초택시',
]
AREA_CDS_ALL = ['11'] * 4500 + ['28'] * 200 + ['31'] * 100 + ['41'] * 100 + ['42'] * 50 + ['43'] * 50

MOBILE_CARRIERS = ['SKT', 'KT', 'LGU+']
PLATE_REGIONS = ['서울', '경기']

# 행정코드
ADMIN_CODES = [
    '1168000000', '1165000000', '1144000000', '1156000000', '1171000000',
    '1174000000', '1138000000', '1111000000', '1114000000', '1120000000',
    '1117000000', '1135000000', '1147000000', '1150000000', '1153000000',
    '1141000000', '1159000000', '1162000000', '1126000000', '1129000000',
]
NUM_ADMIN = len(ADMIN_CODES)

# 관심지역 데이터
INT_AREAS = []
for i, (name, (x, y)) in enumerate(SEOUL_HOTSPOTS.items()):
    INT_AREAS.append({'id': f'A{i+1:04d}', 'name': name, 'cx': x, 'cy': y})
INT_AREA_CXS = np.array([a['cx'] for a in INT_AREAS])
INT_AREA_CYS = np.array([a['cy'] for a in INT_AREAS])

# Pre-generate INT_ZONES (will be populated by gen_m037)
INT_ZONES = []
INT_ZONES_BY_AREA = {}  # area_id -> list of zone_ids


# ============================================================
# Generation functions
# ============================================================

def gen_m002():
    """교통사업자 5,000건"""
    print("  M002 교통사업자 (5,000)...")
    now14 = fmt_dt14(datetime.now())
    rows = []
    for i in range(NUM_BIZR):
        name_base = BASE_BIZR_NAMES[i % len(BASE_BIZR_NAMES)]
        suffix = f'{i // len(BASE_BIZR_NAMES) + 1}' if i >= len(BASE_BIZR_NAMES) else ''
        rows.append({
            'TRANSP_BIZR_ID': TRANSP_BIZR_IDS[i],
            'TRANSP_BIZR_NM': f'{name_base}{suffix}',
            'TEL': f'02-{random.randint(200,999)}-{random.randint(1000,9999)}',
            'AREA_CD': AREA_CDS_ALL[i] if i < len(AREA_CDS_ALL) else '11',
            'USE_YN': 'Y',
            'TRANSP_BIZR_TYPE_CD': str((i % 3) + 1),
            'THREE_PART_WORK_NO': f'{random.randint(1,999):06d}',
            'BIZ_NO': f'{random.randint(100,999)}{random.randint(10,99)}{random.randint(10000,99999)}',
            'EMIS_TRANSP_BIZR_TYPE_CD': f'{(i % 3) + 1:02d}',
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_m001():
    """택시차량 20,000건"""
    print("  M001 택시차량 (20,000)...")
    now14 = fmt_dt14(datetime.now())
    # Vectorized
    hgcl = np.random.choice(['N', 'Y'], size=NUM_VEHC, p=[0.85, 0.15])
    plate_nums = np.random.randint(1000, 9999, size=NUM_VEHC)
    plate_prefixes = np.random.randint(10, 99, size=NUM_VEHC)
    carrier_idx = np.random.randint(0, 3, size=NUM_VEHC)
    region_idx = np.random.randint(0, 2, size=NUM_VEHC)

    rows = []
    for i in range(NUM_VEHC):
        rows.append({
            'TAXI_VEHC_ID': TAXI_VEHC_IDS[i],
            'TRANSP_BIZR_ID': TRANSP_BIZR_IDS[VEHC_BIZR_IDX[i]],
            'VEHC_REGIST_NO': f'{PLATE_REGIONS[region_idx[i]]}{plate_prefixes[i]}바{plate_nums[i]}',
            'MOBILE_SERV_NM': MOBILE_CARRIERS[carrier_idx[i]],
            'DEL_YN': 'N',
            'HGCL_TAXI_YN': hgcl[i],
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_m036():
    """관심지역 3,000건"""
    print("  M036 관심지역 (3,000)...")
    global INT_AREAS
    now14 = fmt_dt14(datetime.now())

    # Expand beyond hotspots: generate grid-based areas across Seoul
    rows = []
    # Keep original 30 hotspots
    for a in INT_AREAS:
        dx, dy = 0.005, 0.003
        rows.append({
            'INT_AREA_ID': a['id'],
            'INT_AREA_NM': a['name'],
            'REMRK': f'{a["name"]} 관심지역',
            'MIN_POS_X': round(a['cx'] - dx, 8),
            'MIN_POS_Y': round(a['cy'] - dy, 8),
            'MAX_POS_X': round(a['cx'] + dx, 8),
            'MAX_POS_Y': round(a['cy'] + dy, 8),
            'MIN_TM_POS_X': round((a['cx'] - dx) * 1000, 8),
            'MIN_TM_POS_Y': round((a['cy'] - dy) * 1000, 8),
            'MAX_TM_POS_X': round((a['cx'] + dx) * 1000, 8),
            'MAX_TM_POS_Y': round((a['cy'] + dy) * 1000, 8),
            'DEL_YN': 'N',
            'REGIST_DTIME': now14,
            'REGISTR_ID': 'ADMIN',
            'LAST_UPT_DTIME': now14,
            'LAST_UPTR_ID': 'ADMIN',
            'DW_LST_UPD_DTM': now14,
        })

    # Generate additional areas (grid + random)
    area_id = len(INT_AREAS) + 1
    district_names = ['동', '서', '남', '북', '중앙', '신', '구', '상', '하', '외곽']
    suffix_names = ['1동', '2동', '3동', '역앞', '사거리', '공원', '시장', '학교앞', '아파트', '빌딩']

    additional_areas = []
    for i in range(3000 - len(INT_AREAS)):
        cx = round(np.random.uniform(126.82, 127.18), 6)
        cy = round(np.random.uniform(37.42, 37.68), 6)
        dx, dy = 0.005, 0.003
        aid = f'A{area_id:04d}'
        area_nm = f'{random.choice(district_names)}{random.choice(suffix_names)}_{area_id}'
        additional_areas.append({'id': aid, 'name': area_nm, 'cx': cx, 'cy': cy})
        rows.append({
            'INT_AREA_ID': aid,
            'INT_AREA_NM': area_nm,
            'REMRK': f'{area_nm} 관심지역',
            'MIN_POS_X': round(cx - dx, 8),
            'MIN_POS_Y': round(cy - dy, 8),
            'MAX_POS_X': round(cx + dx, 8),
            'MAX_POS_Y': round(cy + dy, 8),
            'MIN_TM_POS_X': round((cx - dx) * 1000, 8),
            'MIN_TM_POS_Y': round((cy - dy) * 1000, 8),
            'MAX_TM_POS_X': round((cx + dx) * 1000, 8),
            'MAX_TM_POS_Y': round((cy + dy) * 1000, 8),
            'DEL_YN': 'N',
            'REGIST_DTIME': now14,
            'REGISTR_ID': 'ADMIN',
            'LAST_UPT_DTIME': now14,
            'LAST_UPTR_ID': 'ADMIN',
            'DW_LST_UPD_DTM': now14,
        })
        area_id += 1

    INT_AREAS = INT_AREAS + additional_areas
    return pd.DataFrame(rows)


def gen_m037():
    """관심구역 10,000건"""
    print("  M037 관심구역 (10,000)...")
    global INT_ZONES, INT_ZONES_BY_AREA
    now14 = fmt_dt14(datetime.now())
    rows = []
    zone_seq = 1
    target = 10000
    zones_per_area = max(1, target // len(INT_AREAS))
    remainder = target - zones_per_area * len(INT_AREAS)

    for idx, a in enumerate(INT_AREAS):
        n_zones = zones_per_area + (1 if idx < remainder else 0)
        for j in range(n_zones):
            zid = f'Z{zone_seq:06d}'
            zone_seq += 1
            offset_x = np.random.uniform(-0.003, 0.003)
            offset_y = np.random.uniform(-0.002, 0.002)
            dx, dy = 0.002, 0.001
            cx = a['cx'] + offset_x
            cy = a['cy'] + offset_y
            INT_ZONES.append({'area_id': a['id'], 'zone_id': zid})
            if a['id'] not in INT_ZONES_BY_AREA:
                INT_ZONES_BY_AREA[a['id']] = []
            INT_ZONES_BY_AREA[a['id']].append(zid)
            rows.append({
                'INT_AREA_ID': a['id'],
                'INT_ZONE_ID': zid,
                'INT_ZONE_NM': f'{a["name"]}{j+1}구역',
                'REMRK': '',
                'MIN_POS_X': round(cx - dx, 8),
                'MIN_POS_Y': round(cy - dy, 8),
                'MAX_POS_X': round(cx + dx, 8),
                'MAX_POS_Y': round(cy + dy, 8),
                'MIN_TM_POS_X': round((cx - dx) * 1000, 8),
                'MIN_TM_POS_Y': round((cy - dy) * 1000, 8),
                'MAX_TM_POS_X': round((cx + dx) * 1000, 8),
                'MAX_TM_POS_Y': round((cy + dy) * 1000, 8),
                'DEL_YN': 'N',
                'REGIST_DTIME': now14,
                'REGISTR_ID': 'ADMIN',
                'LAST_UPT_DTIME': now14,
                'LAST_UPTR_ID': 'ADMIN',
                'DW_LST_UPD_DTM': now14,
            })
            if zone_seq > target:
                break
        if zone_seq > target:
            break

    return pd.DataFrame(rows)


def gen_d002():
    """설정 및 서비스정보 20,000건 (차량당 1건)"""
    print("  D002 설정/서비스 (20,000)...")
    now14 = fmt_dt14(datetime.now())
    # Vectorized
    config_vers = np.random.randint(1, 6, size=NUM_VEHC)
    oper_vers = np.random.randint(1, 4, size=NUM_VEHC)
    dtg_setup = np.random.choice(['Y', 'N'], size=NUM_VEHC, p=[0.9, 0.1])

    # Random col_yn_modf times
    secs = random_datetimes_weighted_vec(NUM_VEHC)
    col_times = seconds_to_dt14_batch(secs)

    rows = []
    for i in range(NUM_VEHC):
        vid = TAXI_VEHC_IDS[i]
        rows.append({
            'TRANSP_BIZR_ID': TRANSP_BIZR_IDS[VEHC_BIZR_IDX[i]],
            'TAXI_VEHC_ID': vid,
            'CONFIG_INFO_VER': f'{config_vers[i]:05d}',
            'COL_TARGET_YN': 'Y',
            'COL_YN': 'Y',
            'COL_START_YN': 'Y',
            'COL_YN_MODF_DTIME': col_times[i],
            'OPER_CONFIG_INFO_VER': f'{oper_vers[i]:05d}',
            'DTG_SETUP_YN': dtg_setup[i],
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_d012_chunk(chunk_size, start_seq, total_n):
    """요금정보 chunk 생성 (vectorized)"""
    n = min(chunk_size, total_n - start_seq)
    now14 = fmt_dt14(datetime.now())

    # Vectorized random generation
    secs = random_datetimes_weighted_vec(n)
    # Make PK unique by adding start_seq offset to seconds
    secs = secs + np.arange(n) * 0.001  # tiny offset for uniqueness

    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    compx = np.random.choice(['N', 'Y'], size=n, p=[0.9, 0.1])
    tr_type = np.random.choice(['01', '02', '03'], size=n, p=[0.8, 0.15, 0.05])
    fare_class = np.random.choice(['1', '2', '3'], size=n)
    extra_yn = np.random.choice(['N', 'Y'], size=n, p=[0.7, 0.3])
    off_pay = np.random.choice(['N', 'Y'], size=n, p=[0.95, 0.05])
    pmt_method = np.random.choice(['01', '02', '03', '04'], size=n, p=[0.5, 0.3, 0.15, 0.05])

    # Fares (vectorized)
    base_fare = 4800
    extra_fare = np.minimum(np.random.lognormal(7.5, 0.8, n).astype(int), 100000)
    total_fares = base_fare + (extra_fare // 100) * 100
    total_fares = np.maximum(total_fares, base_fare)

    is_card = np.random.random(n) < 0.75
    card_fares = np.where(is_card, total_fares, 0)
    cash_fares = np.where(is_card, 0, total_fares)
    call_fares = np.random.choice([0, 1000, 2000, 3000], size=n, p=[0.6, 0.2, 0.15, 0.05])
    dis_amts = np.random.choice([0, 500, 1000], size=n, p=[0.8, 0.15, 0.05])
    pltf_fees = np.random.choice([0, 500, 1000, 1500], size=n, p=[0.5, 0.25, 0.2, 0.05])
    fee_model = np.random.choice(['01', '02', '03'], size=n)

    # Distances
    ride_dists = np.clip(np.random.lognormal(8.0, 0.5, n).astype(int), 1000, 50000)
    vacntv_dists = np.clip(np.random.lognormal(7.0, 0.7, n).astype(int), 200, 30000)
    ride_sl_dists = (ride_dists * np.random.uniform(0.5, 0.8, n)).astype(int)

    # Ride duration
    ride_mins = np.clip(np.random.lognormal(2.8, 0.5, n).astype(int), 5, 90)

    # OD coordinates
    o_names, ox, oy, d_names, dx, dy = pick_od_vec(n)

    # Datetime strings
    dt14_list = seconds_to_dt14_batch(secs)
    dt8_list = seconds_to_dt8_batch(secs)
    alight_secs = secs + ride_mins * 60
    alight_dt14 = seconds_to_dt14_batch(alight_secs)
    regist_secs = secs + np.random.randint(60, 1800, n)
    regist_dt14 = seconds_to_dt14_batch(regist_secs)
    recv_secs = secs + np.random.randint(60, 3600, n)
    recv_dt14 = seconds_to_dt14_batch(recv_secs)
    sync_secs = secs + np.random.randint(60, 7200, n)
    sync_dt14 = seconds_to_dt14_batch(sync_secs)

    # Admin codes
    ride_a_idx = np.random.randint(0, NUM_ADMIN, n)
    alight_a_idx = np.random.randint(0, NUM_ADMIN, n)

    # SEQ and UUID - pre-generate
    seqs = np.random.randint(1, 999999, size=n)
    ride_seq_nos = np.random.randint(1, 999, size=n)
    duty_seqs = np.random.randint(1, 3, size=n)

    # Build rows
    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        di = driver_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        did = DRIVER_IDS[di]

        vehc_duty_set = f'{bid}_{vid}_{dt8_list[i]}_{duty_seqs[i]:02d}'

        # Simple UUID (fast)
        uuid_val = f'{start_seq + i:032x}'

        rows.append({
            'COL_DTIME': dt14_list[i],
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'DRIVER_ID': did,
            'COMPX_PAY_YN': compx[i],
            'TR_TYPE': tr_type[i],
            'FARE_CLASS_CD': fare_class[i],
            'CARD_RIDE_FARE': int(card_fares[i]),
            'CASH_RIDE_FARE': int(cash_fares[i]),
            'CALL_FARE': int(call_fares[i]),
            'ETC_FARE': 0,
            'EXTRA_YN': extra_yn[i],
            'RIDE_DTIME': dt14_list[i],
            'RIDE_POS_X': str(ox[i]),
            'RIDE_POS_Y': int(oy[i] * 10000000),
            'ALIGHT_DTIME': alight_dt14[i],
            'ALIGHT_POS_X': str(dx[i]),
            'ALIGHT_POS_Y': int(dy[i] * 10000000),
            'RIDE_DIST': int(ride_dists[i]),
            'VACNTV_DIST': int(vacntv_dists[i]),
            'DIS_AMT': int(dis_amts[i]),
            'MANUAL_INPUT_AMT': 0,
            'PAY_AMT': int(total_fares[i] - dis_amts[i]),
            'PMT_METHOD': pmt_method[i],
            'OFF_PAY': off_pay[i],
            'SEQ': int(seqs[i]),
            'REGIST_DTIME': regist_dt14[i],
            'CRC_ERR_CD': '0',
            'RECV_DTIME': recv_dt14[i],
            'DRIVER_CERT_NO': DRIVER_CERT_NOS[di],
            'VEHC_DUTY_SET_REGIST_NO': vehc_duty_set,
            'RIDE_A_CD': ADMIN_CODES[ride_a_idx[i]],
            'ALIGHT_A_CD': ADMIN_CODES[alight_a_idx[i]],
            'RIDE_INT_AREA_ID': '',
            'RIDE_INT_ZONE_ID': '',
            'ALIGHT_INT_AREA_ID': '',
            'ALIGHT_INT_ZONE_ID': '',
            'DW_LST_UPD_DTM': now14,
            'RIDE_SL_DIST': int(ride_sl_dists[i]),
            'UUID': uuid_val,
            'RIDE_SEQ_NO': f'{ride_seq_nos[i]:03d}',
            'DELAY_PUSH_YN': 'N',
            'PLTF_FEE_AMT': int(pltf_fees[i]),
            'FEE_MODEL_CLASS_CD': fee_model[i],
            'RESERVED': '',
            'SYNC_DTIME': sync_dt14[i],
            'RIDE_POS_Y_ENC': uuid_val[:24],
            'ALIGHT_POS_Y_ENC': uuid_val[8:],
        })
    return pd.DataFrame(rows)


def gen_d012(total=60000000, chunk_size=1000000):
    """요금정보 1,000,000건 (chunked)"""
    print(f"  D012 요금정보 ({total:,}건, chunk={chunk_size:,})...")
    fpath = os.path.join(OUTPUT_DIR, 'DC_TBYXD012.csv')
    written = 0
    for start in range(0, total, chunk_size):
        t0 = time.time()
        df = gen_d012_chunk(chunk_size, start, total)
        if start == 0:
            df.to_csv(fpath, index=False, encoding='utf-8-sig', mode='w')
        else:
            df.to_csv(fpath, index=False, encoding='utf-8-sig', mode='a', header=False)
        written += len(df)
        elapsed = time.time() - t0
        print(f"    chunk {start//chunk_size + 1}: {written:,}/{total:,} ({elapsed:.1f}s)")
        del df
    return written


def gen_d024(n=2000000):
    """일정산 100,000건"""
    print(f"  D024 일정산 ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    secs = random_datetimes_weighted_vec(n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    use_cnts = np.random.randint(5, 41, size=n)
    unit_amts = np.random.randint(8000, 35001, size=n)
    appv_class = np.random.choice(['1', '2'], size=n, p=[0.95, 0.05])

    dt8_list = seconds_to_dt8_batch(secs)
    regist_secs = secs + np.random.randint(3600, 43200, n)
    regist_dt14 = seconds_to_dt14_batch(regist_secs)

    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        did = DRIVER_IDS[driver_idx[i]]
        rows.append({
            'SETTM_DT': dt8_list[i],
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'DRIVER_ID': did,
            'APPV_CANC_CLASS_CD': appv_class[i],
            'USE_CNT': int(use_cnts[i]),
            'USE_AMT': int(use_cnts[i]) * int(unit_amts[i]),
            'REGIST_DTIME': regist_dt14[i],
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_d028(n=2000000):
    """근무SET 100,000건"""
    print(f"  D028 근무SET ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    secs = random_datetimes_weighted_vec(n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    seqs = np.random.randint(1, 10, size=n)
    start_hours = np.random.choice([6, 7, 8, 14, 18, 19, 20], size=n, p=[0.15, 0.2, 0.15, 0.1, 0.15, 0.15, 0.1])
    duty_hours_arr = np.random.choice([8, 10, 12], size=n, p=[0.3, 0.5, 0.2])
    duty_shape = np.random.choice(['01', '02', '03'], size=n)
    duty_conf = np.random.choice(['Y', 'N'], size=n, p=[0.9, 0.1])

    dt8_list = seconds_to_dt8_batch(secs)

    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        di = driver_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        did = DRIVER_IDS[di]
        seq = int(seqs[i])

        # Duty start/end
        day_sec = int(start_hours[i]) * 3600 + np.random.randint(0, 3600)
        duty_start_sec = (secs[i] // 86400) * 86400 + day_sec
        duty_end_sec = duty_start_sec + int(duty_hours_arr[i]) * 3600
        duty_time = int(duty_hours_arr[i]) * 60

        vehc_duty_set = f'{bid}_{vid}_{dt8_list[i]}_{seq:02d}'
        driver_duty_set = f'{did}_{dt8_list[i]}_{seq:02d}'

        ds14 = seconds_to_dt14_batch([duty_start_sec])[0]
        de14 = seconds_to_dt14_batch([duty_end_sec])[0]
        reg14 = seconds_to_dt14_batch([duty_start_sec + np.random.randint(0, 600)])[0]

        rows.append({
            'DUTY_DT': dt8_list[i],
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'SEQ': seq,
            'VEHC_DUTY_SET_REGIST_NO': vehc_duty_set,
            'DRIVER_CERT_NO': DRIVER_CERT_NOS[di],
            'DUTY_START_DTIME': ds14,
            'DUTY_END_DTIME': de14,
            'DUTY_TIME': duty_time,
            'DUTY_SHAPE_CD': duty_shape[i],
            'DUTY_CONF_YN': duty_conf[i],
            'FARE_OCCUR_YN': 'Y',
            'DRIVER_DUTY_SET_REGIST_NO': driver_duty_set,
            'REGIST_DTIME': reg14,
            'REGISTR_ID': 'SYSTEM',
            'LAST_UPT_DTIME': now14,
            'LAST_UPTR_ID': 'SYSTEM',
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_h002_chunk(chunk_size, start_seq):
    """위치정보 chunk"""
    n = chunk_size
    now14 = fmt_dt14(datetime.now())
    secs = random_datetimes_weighted_vec(n)
    # Ensure uniqueness with start_seq offset
    secs = secs + (np.arange(n) + start_seq) * 0.001

    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    tc_class = np.random.choice([1, 2, 3], size=n)
    tc_ids_idx = np.random.randint(0, 2000, size=n)  # 2000 terminals
    altitudes = np.round(np.random.uniform(10, 100, n), 1)
    street_class = np.random.choice(['1', '2', '3', '4'], size=n)
    serv_class = np.random.choice(['1', '2', '3'], size=n, p=[0.5, 0.3, 0.2])
    azimuths = np.random.randint(0, 361, size=n)
    speeds = np.clip(np.random.normal(30, 15, n).astype(int), 0, 120)

    x, y = coord_near_hotspot_vec(n)
    dt14_list = seconds_to_dt14_batch(secs)

    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        tc_id = f'TC{tc_ids_idx[i]:018d}'

        rows.append({
            'COL_DTIME': dt14_list[i],
            'COL_TC_CLASS_CD': int(tc_class[i]),
            'TC_ID': tc_id,
            'TAXI_VEHC_ID': vid,
            'TRANSP_BIZR_ID': bid,
            'ALTITD': float(altitudes[i]),
            'STREE_CLASS_CD': street_class[i],
            'SERV_CLASS_CD': serv_class[i],
            'TACO_AZIMUTH': int(azimuths[i]),
            'TACO_SPD': int(speeds[i]),
            'DRIVER_ID': DRIVER_IDS[driver_idx[i]],
            'DW_LST_UPD_DTM': now14,
            'POS_X': str(x[i]),
            'POS_Y_ENC': f'{start_seq + i:024x}',
        })
    return pd.DataFrame(rows)


def gen_h002(total=20000000, chunk_size=1000000):
    """위치정보 3,000,000건 (chunked)"""
    print(f"  H002 위치정보 ({total:,}건, chunk={chunk_size:,})...")
    fpath = os.path.join(OUTPUT_DIR, 'DC_TBYXH002.csv')
    written = 0
    for start in range(0, total, chunk_size):
        t0 = time.time()
        actual_chunk = min(chunk_size, total - start)
        df = gen_h002_chunk(actual_chunk, start)
        if start == 0:
            df.to_csv(fpath, index=False, encoding='utf-8-sig', mode='w')
        else:
            df.to_csv(fpath, index=False, encoding='utf-8-sig', mode='a', header=False)
        written += len(df)
        elapsed = time.time() - t0
        print(f"    chunk {start//chunk_size + 1}: {written:,}/{total:,} ({elapsed:.1f}s)")
        del df
    return written


def gen_s002(n=4000000):
    """운행통계 200,000건"""
    print(f"  S002 운행통계 ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    dates = random_dates8_vec(n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    ride_cnts = np.random.randint(5, 41, size=n)
    biz_times = np.random.randint(300, 721, size=n)
    biz_dists = np.random.randint(50000, 250001, size=n)
    vacntv_ratios = np.random.uniform(0.2, 0.5, n)
    real_ratios = np.random.uniform(0.5, 0.8, n)

    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        did = DRIVER_IDS[driver_idx[i]]
        rc = int(ride_cnts[i])
        bt = int(biz_times[i])
        bd = int(biz_dists[i])
        rows.append({
            'STAT_DT': dates[i],
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'DRIVER_ID': did,
            'RIDE_CNT': rc,
            'BIZ_TIME': bt,
            'AVRG_BIZ_TIME': bt // rc,
            'VACNTV_TIME': int(bt * vacntv_ratios[i]),
            'BIZ_DIST': bd,
            'AVRG_BIZ_DIST': bd // rc,
            'REAL_DIST': int(bd * real_ratios[i]),
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_s003(n=4000000):
    """결제통계 200,000건"""
    print(f"  S003 결제통계 ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    dates = random_dates8_vec(n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    pp_cnts = np.random.randint(0, 11, size=n)
    cc_cnts = np.random.randint(5, 31, size=n)
    cash_cnts = np.random.randint(0, 11, size=n)
    canc_cnts = np.random.randint(0, 3, size=n)
    pp_unit = np.random.randint(5000, 30001, size=n)
    cc_unit = np.random.randint(8000, 40001, size=n)
    canc_unit = np.random.randint(5000, 20001, size=n)
    cash_unit = np.random.randint(5000, 35001, size=n)

    rows = []
    for i in range(n):
        vi = vehc_idx[i]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        did = DRIVER_IDS[driver_idx[i]]
        rows.append({
            'STAT_DT': dates[i],
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'DRIVER_ID': did,
            'PPCARD_AMT': int(pp_cnts[i]) * int(pp_unit[i]),
            'PPCARD_CNT': int(pp_cnts[i]),
            'CCARD_AMT': int(cc_cnts[i]) * int(cc_unit[i]),
            'CCARD_CNT': int(cc_cnts[i]),
            'CARD_CANC_AMT': int(canc_cnts[i]) * int(canc_unit[i]),
            'CARD_CANC_CNT': int(canc_cnts[i]),
            'CASH_AMT': int(cash_cnts[i]) * int(cash_unit[i]),
            'CASH_CNT': int(cash_cnts[i]),
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_s004(n=4000000):
    """운행통계-종사자 200,000건"""
    print(f"  S004 운행통계-종사자 ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    dates = random_dates8_vec(n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    ride_cnts = np.random.randint(5, 41, size=n)
    biz_times = np.random.randint(300, 721, size=n)
    biz_dists = np.random.randint(50000, 250001, size=n)
    vacntv_ratios = np.random.uniform(0.2, 0.5, n)
    real_ratios = np.random.uniform(0.5, 0.8, n)
    login_hours = np.random.randint(5, 9, size=n)
    login_mins = np.random.randint(0, 60, size=n)
    login_days = np.random.randint(0, DATE_RANGE_DAYS, size=n)

    rows = []
    for i in range(n):
        di = driver_idx[i]
        vi = vehc_idx[i]
        did = DRIVER_IDS[di]
        cert_no = DRIVER_CERT_NOS[di]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        rc = int(ride_cnts[i])
        bt = int(biz_times[i])
        bd = int(biz_dists[i])

        login_sec = int(login_days[i]) * 86400 + int(login_hours[i]) * 3600 + int(login_mins[i]) * 60
        login_dt14 = seconds_to_dt14_batch([login_sec])[0]

        rows.append({
            'STAT_DT': dates[i],
            'DRIVER_CERT_NO': cert_no,
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'RIDE_CNT': rc,
            'BIZ_TIME': bt,
            'AVRG_BIZ_TIME': bt // rc,
            'VACNTV_TIME': int(bt * vacntv_ratios[i]),
            'BIZ_DIST': bd,
            'AVRG_BIZ_DIST': bd // rc,
            'REAL_DIST': int(bd * real_ratios[i]),
            'FIRST_LOGIN_DTIME': login_dt14,
            'DW_LST_UPD_DTM': now14,
        })
    return pd.DataFrame(rows)


def gen_s005(n=4000000):
    """결제통계-종사자 200,000건"""
    print(f"  S005 결제통계-종사자 ({n:,})...")
    now14 = fmt_dt14(datetime.now())
    dates = random_dates8_vec(n)
    driver_idx = np.random.randint(0, NUM_DRIVERS, size=n)
    vehc_idx = np.random.randint(0, NUM_VEHC, size=n)
    pp_cnts = np.random.randint(0, 11, size=n)
    cc_cnts = np.random.randint(5, 31, size=n)
    canc_cnts = np.random.randint(0, 3, size=n)
    pp_unit = np.random.randint(5000, 30001, size=n)
    cc_unit = np.random.randint(8000, 40001, size=n)
    canc_unit = np.random.randint(5000, 20001, size=n)

    rows = []
    for i in range(n):
        di = driver_idx[i]
        vi = vehc_idx[i]
        cert_no = DRIVER_CERT_NOS[di]
        vid = TAXI_VEHC_IDS[vi]
        bid = TRANSP_BIZR_IDS[VEHC_BIZR_IDX[vi]]
        rows.append({
            'STAT_DT': dates[i],
            'DRIVER_CERT_NO': cert_no,
            'TRANSP_BIZR_ID': bid,
            'TAXI_VEHC_ID': vid,
            'PPCARD_AMT': int(pp_cnts[i]) * int(pp_unit[i]),
            'PPCARD_CNT': int(pp_cnts[i]),
            'CCARD_AMT': int(cc_cnts[i]) * int(cc_unit[i]),
            'CCARD_CNT': int(cc_cnts[i]),
            'CARD_CANC_AMT': int(canc_cnts[i]) * int(canc_unit[i]),
        })
    return pd.DataFrame(rows)


# ============================================================
# 메인 실행
# ============================================================
if __name__ == '__main__':
    t_start = time.time()
    print("=" * 60)
    print("목데이터 100x 생성 시작!")
    print("=" * 60)

    # 1. 마스터 먼저 (FK 참조용)
    df_m002 = gen_m002()
    df_m002.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXM002.csv'), index=False, encoding='utf-8-sig')

    df_m001 = gen_m001()
    df_m001.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXM001.csv'), index=False, encoding='utf-8-sig')

    df_m036 = gen_m036()
    df_m036.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXM036.csv'), index=False, encoding='utf-8-sig')

    df_m037 = gen_m037()
    df_m037.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXM037.csv'), index=False, encoding='utf-8-sig')

    df_d002 = gen_d002()
    df_d002.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXD002.csv'), index=False, encoding='utf-8-sig')

    # 2. 중간 크기 트랜잭션
    df_d028 = gen_d028(2000000)
    df_d028.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXD028.csv'), index=False, encoding='utf-8-sig')
    del df_d028

    df_d024 = gen_d024(2000000)
    df_d024.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXD024.csv'), index=False, encoding='utf-8-sig')
    del df_d024

    # 3. 통계 테이블
    df_s002 = gen_s002(4000000)
    df_s002.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXS002.csv'), index=False, encoding='utf-8-sig')
    del df_s002

    df_s003 = gen_s003(4000000)
    df_s003.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXS003.csv'), index=False, encoding='utf-8-sig')
    del df_s003

    df_s004 = gen_s004(4000000)
    df_s004.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXS004.csv'), index=False, encoding='utf-8-sig')
    del df_s004

    df_s005 = gen_s005(4000000)
    df_s005.to_csv(os.path.join(OUTPUT_DIR, 'DC_TBYXS005.csv'), index=False, encoding='utf-8-sig')
    del df_s005

    # 4. 대용량 테이블 (chunked)
    n_d012 = gen_d012(60000000, chunk_size=1000000)
    n_h002 = gen_h002(20000000, chunk_size=1000000)

    # 5. 결과 보고
    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}")
    print(f"생성 완료! (총 {elapsed:.1f}초)")
    print(f"{'=' * 60}")

    file_list = [
        'DC_TBYXM001.csv', 'DC_TBYXM002.csv', 'DC_TBYXM036.csv', 'DC_TBYXM037.csv',
        'DC_TBYXD002.csv', 'DC_TBYXD012.csv', 'DC_TBYXD024.csv', 'DC_TBYXD028.csv',
        'DC_TBYXH002.csv',
        'DC_TBYXS002.csv', 'DC_TBYXS003.csv', 'DC_TBYXS004.csv', 'DC_TBYXS005.csv',
    ]
    total_rows = 0
    for fname in file_list:
        fpath = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            # Count lines (subtract 1 for header)
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                line_count = sum(1 for _ in f) - 1
            print(f"  {fname:25s} {line_count:>12,}건  ({size_mb:>8.1f} MB)")
            total_rows += line_count
        else:
            print(f"  {fname:25s} NOT FOUND")
    print(f"\n  총 {total_rows:,}건, {len(file_list)}개 파일")
    print(f"  총 소요시간: {elapsed:.1f}초")
