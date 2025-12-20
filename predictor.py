# predictor.py
import os
import datetime
import joblib
import pandas as pd
import numpy as np
import requests

# 서버 시작 시 1번만 로드
MODELS = joblib.load("real_estate_model_simple.pkl")

KAKAO_API_KEY = "c6943568281ead90d30d6c07d618eb7d"

# (코랩 코드 기반) 건대 좌표
KONKUK_UNIV_COORDS = (37.5408, 127.0794)

# (코랩 코드 기반) 주요 역 좌표 (건대 주변)
STATION_COORDS = {
    "건대입구역": (37.540458, 127.069320),
    "강변역": (37.535102, 127.094761),
    "구의역": (37.537190, 127.086164),
    "군자역": (37.557200, 127.079546),
    "아차산역": (37.551944, 127.089722),
    "광나루역": (37.545291, 127.103485),
    "자양역": (37.531667, 127.066667),
    "어린이대공원역": (37.547778, 127.074444),
}

# 금리 맵(없는 달은 3.0으로)
rate_map = {
    202501: 3.00, 202502: 2.75, 202503: 2.75, 202504: 2.75,
    202505: 2.50, 202506: 2.50, 202507: 2.50, 202508: 2.50,
    202509: 2.50, 202510: 2.50, 202511: 2.50, 202512: 2.50
}


def _address_to_coords(address: str) -> tuple[float, float]:

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}

    resp = requests.get(url, headers=headers, params=params, timeout=5).json()
    if not resp.get("documents"):
        raise ValueError("주소를 좌표로 변환할 수 없습니다. (주소 형식/키를 확인하세요)")

    doc = resp["documents"][0]
    lat = float(doc["y"])
    lon = float(doc["x"])
    return lat, lon


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return float(R * c)


def _nearest_station_dist_km(lat: float, lon: float) -> float:
    dmin = float("inf")
    for (slat, slon) in STATION_COORDS.values():
        d = _haversine_km(lat, lon, slat, slon)
        if d < dmin:
            dmin = d
    return float(dmin)


def _current_rate_and_proxy() -> tuple[float, float]:
    # proxy(주간변동률) 파일을 서버가 들고있지 않으므로 우선 0 고정
    # (나중에 proxy를 서버에 올리면 여기만 업데이트)
    now = datetime.datetime.now()
    ym = int(now.strftime("%Y%m"))
    rate = float(rate_map.get(ym, 3.0))
    proxy = 0.0
    return rate, proxy


def predict_price(
    housing_type: str,   # '오피스텔' | '연립다세대'
    rent_type: str,      # '전세' | '월세'
    address: str,
    area: float,
    floor: int,
    year_built: int
) -> float:
    if (housing_type, rent_type) not in MODELS:
        raise KeyError(f"모델이 없습니다: {(housing_type, rent_type)}")

    xgb, lgbm, feature_list = MODELS[(housing_type, rent_type)]

    lat, lon = _address_to_coords(address)

    now = datetime.datetime.now()
    building_age = max(now.year - int(year_built), 0)

    school_dist = _haversine_km(lat, lon, KONKUK_UNIV_COORDS[0], KONKUK_UNIV_COORDS[1])
    station_dist = _nearest_station_dist_km(lat, lon)

    rate, proxy = _current_rate_and_proxy()

    # 월세 보증금 1000 고정(요구사항)
    deposit_fixed = 1000.0

    # 공통 feature 풀(모델이 요구하는 키만 꺼내 쓰게 됨)
    feats = {
        "전용면적(㎡)": float(area),
        "층": int(floor),
        "건축년도": int(year_built),

        "위도": float(lat),
        "경도": float(lon),

        "학교거리": float(school_dist),
        "역거리": float(station_dist),

        "건물나이": float(building_age),
        "금리": float(rate),
        "주간변동률": float(proxy),

        "보증금(만원)": float(deposit_fixed),
    }

    # feature_list 순서로 DataFrame 구성 (없는 값은 0)
    X = pd.DataFrame([[feats.get(f, 0) for f in feature_list]], columns=feature_list)

    pred1 = float(xgb.predict(X)[0])
    pred2 = float(lgbm.predict(X)[0])

    out = (pred1 + pred2) / 2.0
    return float(max(out, 0.0))
