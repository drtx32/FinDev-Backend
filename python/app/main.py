from typing import AsyncGenerator, Literal, Any
from fastapi import FastAPI, Request, Depends
from pydantic import BaseModel

import time
import redis
# import mysql.connector
import psycopg
from os import environ

from ashare_core.crawler import em_web, ths_web, ths_app, jyhf_app, jygs_web
from ashare_core.tool import SessionManager


# =========================== 定义数据模型 ============================
...

# ============================ 初始化服务连接 ============================


def get_redis_client() -> redis.Redis:
    return redis.Redis(host=environ.get('REDIS_HOST', 'redis'), port=6379, db=0)


# 替换: MySQL -> PostgreSQL
def get_postgres_connection() -> psycopg.Connection:
    max_retries = 10
    delay = 2
    last_err = None
    for i in range(max_retries):
        try:
            return psycopg.connect(
                host=environ.get('POSTGRES_HOST', 'postgres'),
                port=int(environ.get("POSTGRES_PORT", 5432)),
                user=environ.get('POSTGRES_USER', 'appuser'),
                password=environ.get('POSTGRES_PASSWORD', 'apppass'),
                dbname=environ.get('POSTGRES_DB', 'appdb'),
                connect_timeout=5
            )
        except Exception as e:
            last_err = e
            print(f"[PostgreSQL] 第{i+1}次连接失败: {e}, {delay}s后重试...")
            time.sleep(delay)
    raise last_err


async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    # 初始化连接
    redis_client = get_redis_client()
    pg_conn = None
    session_manager = SessionManager(3600)
    try:
        # 验证 Redis 连接
        redis_client.ping()
    except Exception as e:
        print(f"Redis 连接失败: {e}")
        redis_client = None
    try:
        # 验证 PostgreSQL 连接
        pg_conn = get_postgres_connection()
    except Exception as e:
        print(f"PostgreSQL 连接失败: {e}")
        pg_conn = None
    # 挂载到 app.state
    app.state.redis_client = redis_client
    app.state.pg_conn = pg_conn
    app.state.session_manager = session_manager
    yield
    # 关闭连接
    if redis_client:
        try:
            redis_client.close()
        except Exception:
            pass
    if pg_conn:
        try:
            pg_conn.close()
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)


# ============================ 定义 API ============================
def get_services(request: Request) -> tuple[redis.Redis, psycopg.Connection]:
    return request.app.state.redis_client, request.app.state.pg_conn


def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello, World! This is FinDev-Backend."}


@app.get("/health")
def health_check(services=Depends(get_services)) -> dict[str, Any]:
    redis_client, pg_conn = services
    redis_ok = False
    pg_ok = False
    # 检查 Redis
    if redis_client:
        try:
            redis_client.ping()
            redis_ok = True
        except Exception:
            pass
    # 检查 PostgreSQL
    if pg_conn:
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT 1")
            pg_ok = True
        except Exception:
            pass
    return {
        "status": "healthy" if (redis_ok and pg_ok) else "unhealthy",
        "services": {
            "redis": "up" if redis_ok else "down",
            "postgres": "up" if pg_ok else "down"
        }
    }


@app.get("/em_guba/stock_history_rank")
def crawl_em_stock_history_rank(
    symbol: str,
    type: Literal['120d', '0.5y', '1y', '1ly'] = "1y",
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = em_web.stock_history_rank(
        symbol,
        type=type,
        session=session.create_or_get("em_guba", "Session", use_http=False)
    )
    return {
        "result": data.to_dict("split"),
        "symbol": symbol,
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/ths_app/plate_stats")
def crawl_ths_plate_stats(
    type: Literal['concept', 'industry', 'region', 'style'] | None = None,
    index: int = 0,
    pagesize: int = 10,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    type_map = {
        'concept': '概念',
        'industry': '行业',
        'region': '地域',
        'style': '风格'
    }
    data = ths_app.plateStats(
        type_map.get(type),
        index=index,
        pagesize=pagesize,
        session=session.create_or_get("ths_app", "Session")
    )
    return {
        "result": data.to_dict("split"),
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/ths_l2/hot_plate_circle")
def crawl_ths_hot_plate_circle(
    days: Literal[10, 30] = 30,
    type: Literal['industry', 'concept'] | None = None,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    name_df, code_df, rank_df = ths_app.l2_hotPlateCircle(
        days=days,
        type=type,
        session=session.create_or_get("ths_l2", "Session")
    )
    return {
        "result": {
            "name": name_df.to_dict("split"),
            "code": code_df.to_dict("split"),
            "rank": rank_df.to_dict("split")
        },
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/ths_web/stock")
def crawl_ths_stock(
    symbol: str,
    period: Literal[
        'daily', 'weekly', 'monthly', 'quarterly', 'yearly',
        '1min', '5min', '30min', '60min', '240min'
    ] = 'daily',
    adjust: Literal['bfq', 'qfq', 'hfq'] = 'qfq',
    size: int = 250,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    period_map = {
        'daily': '日线',
        'weekly': '周线',
        'monthly': '月线',
        'quarterly': '季线',
        'yearly': '年线',
        '1min': '1分钟线',
        '5min': '5分钟线',
        '30min': '30分钟线',
        '60min': '60分钟线',
        '240min': '240分钟线'
    }
    fq_map = {
        'bfq': '不复权',
        'qfq': '前复权',
        'hfq': '后复权'
    }
    data = ths_web.ths_stock(
        symbol,
        period=period_map.get(period),
        adjust=fq_map.get(adjust),
        size=size,
        session=session.create_or_get("ths_web", "Session")
    )
    return {
        "result": data.to_dict("split"),
        "symbol": symbol,
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/em_web/stock")
def crawl_em_stock(
    symbol: str,
    period: Literal[
        'daily', 'weekly', 'monthly', '1min', '5min', '30min', '60min', '240min'
    ] = 'daily',
    adjust: Literal['bfq', 'qfq', 'hfq'] = 'qfq',
    start_date: str = "1970-01-01",
    end_date: str = "2050-01-01",
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    period_map = {
        'daily': '日线',
        'weekly': '周线',
        'monthly': '月线',
        'quarterly': '季线',
        'yearly': '年线',
        '1min': '1分钟线',
        '5min': '5分钟线',
        '30min': '30分钟线',
        '60min': '60分钟线',
        '240min': '240分钟线'
    }
    fq_map = {
        'bfq': '不复权',
        'qfq': '前复权',
        'hfq': '后复权'
    }
    data = em_web.em_stock(
        symbol,
        period=period_map.get(period),
        adjust=fq_map.get(adjust),
        start_date=start_date,
        end_date=end_date,
        session=session.create_or_get("em_web", "Session")
    )
    return {
        "result": data.to_dict("split"),
        "symbol": symbol,
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/jygs_web/companies")
def crawl_jygs_companies(
    keyword: str = None,
    pagesize: int = 50,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = jygs_web.get_companies(
        keyword=keyword,
        pagesize=pagesize,
        session=session.create_or_get("jygs_web", "Session", use_http=False)
    )
    return {
        "result": data.to_dict("split"),
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/jygs_web/announcement")
def crawl_jygs_announcement(
    keyword: str = None,
    pagesize: int = 50,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = jygs_web.announcement(
        keyword=keyword,
        pagesize=pagesize,
        session=session.create_or_get("jygs_web", "Session", use_http=False)
    )
    return {
        "result": data.to_dict("split"),
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/jygs_web/industry")
def crawl_jygs_industry(
    keyword: str = None,
    pagesize: int = 50,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = jygs_web.industry(
        keyword=keyword,
        pagesize=pagesize,
        session=session.create_or_get("jygs_web", "Session", use_http=False)
    )
    return {
        "result": data.to_dict("split"),
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/jyhf_app/theme_list")
def crawl_jyhf_theme(
    sort_by: str = "pctChg",
    ascending: bool = False,
    authorization: str = None,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = jyhf_app.themeList(
        sort_by=sort_by,
        ascending=ascending,
        authorization=authorization,
        session=session.create_or_get("jyhf_app", "Session", use_http=False)
    )
    return {
        "result": data.to_dict("split"),
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/jyhf_app/theme_detail")
def crawl_jyhf_theme_detail(
    id: str,
    date: str = None,
    index: int = 0,
    pagesize: int = 1201,
    sort_by: str = "pctChg",
    ascending: bool = False,
    authorization: str = None,
    session=Depends(get_session_manager)
) -> dict[str, Any]:
    session: SessionManager
    data = jyhf_app.themeStockPerformance(
        theme_id=id,
        date=date,
        index=index,
        pagesize=pagesize,
        sort_by=sort_by,
        ascending=ascending,
        authorization=authorization,
        session=session.create_or_get(
            "jyhf_app", "Session", use_http=False, check="json")
    )
    return {
        "result": data.to_dict("split"),
        "id": id,
        "size": data.shape[0],
        "status": "success",
        "timestamp": int(time.time())
    }


@app.get("/version")
def get_version() -> dict[str, str]:
    return {
        "service": "FinDev-Backend",
        "version": "0.1.0",
        "ashare_core": "v1.0.6",
    }
