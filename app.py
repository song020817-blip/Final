from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


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
        # 개발 중 테스트가 필요하면 아래 주석을 해제하세요.
        # "http://localhost:3000",
        # "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 3) 입력값 검증용 Enum
# =========================
class HousingType(str, Enum):
    villa = "연립다세대"
    officetel = "오피스텔"


class RentType(str, Enum):
    jeonse = "전세"
    wolse = "월세"


# =========================
# 4) 요청/응답 스키마
# =========================
class PredictRequest(BaseModel):
    address: str = Field(..., min_length=2, description="시군구+번지 포함 주소")
    area: float = Field(..., gt=0, description="면적(㎡)")
    floor: int = Field(..., description="층수")
    year_built: int = Field(..., ge=1900, le=2100, description="준공년도")
    housing_type: HousingType = Field(..., description="주택유형(연립다세대/오피스텔)")
    rent_type: RentType = Field(..., description="전월세구분(전세/월세)")


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
# 6) 예측 API (현재는 더미 로직)
#    - 나중에 여기만 ML 모델 예측으로 교체하면 됨
# =========================
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """
    최종 스펙 기준 예측 API.
    현재는 더미(임시) 예측 로직이며,
    추후 ML 모델 연결 시 이 함수 내부만 교체하면 됩니다.
    """
    # 계약년월 입력을 받지 않는 스펙이므로, 연식은 "대략값"으로만 반영
    # (진짜 모델 연결 시에는 계약년월/시장지표 등을 백엔드에서 내부적으로 붙이면 됩니다.)
    approx_age = max(2025 - req.year_built, 0)  # 임시 기준연도

    # 주택유형 가중치(임시)
    if req.housing_type == HousingType.officetel:
        type_mult = 1.05
    else:  # 연립다세대
        type_mult = 0.95

    # 더미 보증금 예측(만원 단위 느낌으로 만든 임시값)
    deposit = (req.area * 450 + req.floor * 25 - approx_age * 8) * type_mult
    deposit = max(deposit, 0)

    # 전월세 구분에 따른 월세 처리
    if req.rent_type == RentType.jeonse:
        monthly = 0.0
    else:
        # 월세 더미: 면적/층/연식 영향만 가볍게 반영
        monthly = req.area * 1.8 + max(0, 10 - req.floor) * 1.2 + approx_age * 0.15
        monthly = max(monthly, 0)

    return PredictResponse(
        deposit_pred=float(round(deposit, 2)),
        monthly_pred=float(round(monthly, 2)),
    )
