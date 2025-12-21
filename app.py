from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from crawler import run_crawler
import psycopg2

app = FastAPI()

def get_db_conn():
    return psycopg2.connect(
        host="localhost",
        port=5433,
        database="postgres",
        user="postgres",
        password="postgres"
    )

# ========== CORS 설정 (반드시 라우트 정의 전에!) ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # 모든 도메인 허용
    allow_credentials=True,           # ✅ True로 설정!
    allow_methods=["*"],              # 모든 HTTP 메서드 허용
    allow_headers=["*"],              # 모든 헤더 허용
)


# ========== 기존 크롤링 API ==========
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
            first = result[0]
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


# ========== ✅ 예측 API (이 부분이 꼭 필요해요!) ==========
class PredictRequest(BaseModel):
    address: str
    area: float
    floor: int
    year_built: int
    housing_type: str
    rent_type: str

@app.post("/predict")
async def predict(data: PredictRequest):
    """
    부동산 가격 예측 API
    """
    try:
        # 임시 더미 값 (나중에 실제 모델로 교체)
        deposit_pred = 10000  # 보증금 (만원)
        monthly_pred = 50     # 월세 (만원)
        
        return {
            "deposit_pred": deposit_pred,
            "monthly_pred": monthly_pred
        }
        
    except Exception as e:
        print(f"예측 실패: {e}")
        return {
            "error": str(e),
            "deposit_pred": 0,
            "monthly_pred": 0
        }


# ========== 정적 파일 서비스 (맨 마지막!) ==========
app.mount("/", StaticFiles(directory="html", html=True), name="html")
