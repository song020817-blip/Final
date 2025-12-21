from enum import Enum
import os
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from predictor import predict_price


# =========================
# 1) 앱 생성
# =========================
app = FastAPI(title="Gwangjin Rent Prediction API")


# =========================
# 2) CORS (Netlify 연결용)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vocal-maamoul-60eaa6.netlify.app",
        # 개발 중 필요 시:
        # "http://localhost:3000",
        # "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 3) Enum 정의
# =========================
class HousingType(str, Enum):
    villa = "연립다세대"
    officetel = "오피스텔"


class RentType(str, Enum):
    jeonse = "전세"
    wolse = "월세"


# =========================
# 4) Request / Response
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
# 5) 헬스체크
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# 6) 유틸: 주소 → 위도/경도
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
# 7) 예측 API (실제 모델 연결)
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

from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="html", html=True), name="html")
