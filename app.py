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


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1) ★ API 라우트를 static mount보다 위에 둔다 ★
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




# 2) ★ html 폴더 전체를 정적 파일로 서비스 (API보다 아래에 위치) ★
app.mount("/", StaticFiles(directory="html", html=True), name="html")
