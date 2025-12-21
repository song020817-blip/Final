from enum import Enum
import os
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path

import psycopg2

from predictor import predict_price
from crawler import run_crawler


# =========================
# 1) 앱 생성 (단 1번만)
# =========================
app = FastAPI(title="Gwangjin Rent Prediction API")


# =========================
# 2) CORS (둘을 합쳐서 한 번만)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vocal-maamoul-60eaa6.netlify.app",
        "https://gogeous-chimera-a243.netlify.app",
        "*",  # resident 쪽이 allow_origins=["*"]였으므로 병합
    ],
    allow_credentials=False,   # resident 코드가 False였음
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 3) 정적 파일 mount (충돌 방지)
# - 기존 predict는 /ui 로 제공
# - resident는 / 로 제공
# =========================
BASE_DIR = Path(__file__).resolve().parent
HTML_DIR = BASE_DIR / "html"

# /ui 아래로 정적파일 제공 (예: /ui/predict.html)
if HTML_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(HTML_DIR), html=True), name="ui")

# resident에서 원래 "/"로 mount 했으므로 그대로 둠
# (주의: "/"로 mount 하면 사실상 대부분의 페이지가 여기로 들어가므로
# /ui를 먼저 mount 해두는 게 안전)
if HTML_DIR.exists():
    app.mount("/", StaticFiles(directory=str(HTML_DIR), html=True), name="html")


# =========================
# 4) Enum 정의 (predict 코드 그대로)
# =========================
class HousingType(str, Enum):
    villa = "연립다세대"
    officetel = "오피스텔"


class RentType(str, Enum):
    jeonse = "전세"
    wolse = "월세"


# =========================
# 5) Request / Response (predict 코드 그대로)
# =========================
class PredictRequest(BaseModel):
    address: str = Field(..., min_length=2, description="시군구+번지 포함 주소")
    area: float = Field(..., gt=0, description="전용면적(㎡)")
    floor: int = Field(..., description="층수")
    year_built: int = Field(..., ge=1900, le=2100, description="준공년도")
    housing_type: HousingType
    rent_type: RentType


class PredictResponse(BaseModel):
    deposit_pred: float
    monthly_pred: float


# =========================
# 6) 헬스체크 (predict 코드 그대로)
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# 7) 유틸: 주소 → 위도/경도 (predict 코드 그대로)
# =========================
def get_lat_lng_from_address(address: str):
    kakao_key = os.getenv("KAKAO_API_KEY")
    if not kakao_key:
        raise HTTPException(status_code=500, detail="KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    params = {"query": address}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=3)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="카카오 주소 API 호출 실패")

    if not data.get("documents"):
        raise HTTPException(status_code=400, detail="주소를 좌표로 변환할 수 없습니다.")

    lon = float(data["documents"][0]["x"])
    lat = float(data["documents"][0]["y"])
    return lat, lon


# =========================
# 8) 예측 API (predict 코드 그대로)
# =========================
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):

    # 전세: 보증금 예측, 월세=0
    if req.rent_type == RentType.jeonse:
        deposit = predict_price(
            housing_type=req.housing_type.value,
            rent_type="전세",
            address=req.address,
            area=req.area,
            floor=req.floor,
            year_built=req.year_built
        )
        return PredictResponse(deposit_pred=deposit, monthly_pred=0.0)

    # 월세: 보증금=1000 고정, 월세 예측
    monthly = predict_price(
        housing_type=req.housing_type.value,
        rent_type="월세",
        address=req.address,
        area=req.area,
        floor=req.floor,
        year_built=req.year_built
    )
    return PredictResponse(deposit_pred=1000.0, monthly_pred=monthly)


# =========================
# 9) DB 연결 (resident 코드 그대로)
# =========================
def get_db_conn():
    return psycopg2.connect(
        host="localhost",
        port=5433,
        database="postgres",
        user="postgres",
        password="postgres"
    )


# =========================
# 10) resident용 Request + API (resident 코드 그대로)
# =========================
class CrawlRequest(BaseModel):
    tp: str
    addr: str
    sido: str
    sigungu: str
    road: str
    bldg: str


@app.post("/api/crawl")
def crawl(data: CrawlRequest):
    result = run_crawler(
        tp=data.tp,
        addr=data.addr,
        sido=data.sido,
        sigungu=data.sigungu,
        road=data.road,
        bldg=data.bldg
    )

    # ===== 검색 결과가 있을 때만 로그 저장 =====
    if result and isinstance(result, list) and len(result) > 0:
        try:
            first = result[0]  # 대표값: 첫 번째 거래

            deposit_raw = first.get("보증금(만원)")
            monthly_raw = first.get("월세(만원)")

            deposit = int(deposit_raw.replace(",", "")) if deposit_raw else None
            monthly = int(monthly_raw.replace(",", "")) if monthly_raw else None

            conn = get_db_conn()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO user_action_log
                (tab_type, complex_name, region, deposit, monthly_rent)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "resident",
                    data.bldg,
                    data.sigungu,
                    deposit,
                    monthly
                )
            )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print("로그 저장 실패:", e)

    return {"success": True, "result": result}
