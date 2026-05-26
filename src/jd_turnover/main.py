"""FastAPI 应用入口。

启动: uvicorn jd_turnover.main:app --host 0.0.0.0 --port 8000
"""

import os
import secrets
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from jinja2 import Environment, FileSystemLoader
from loguru import logger

from jd_turnover.config import UPLOAD_DIR, OUTPUT_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB, ACCESS_PASSWORD
from jd_turnover.data.loader import load_file
from jd_turnover.data.cleaner import drop_empty_rows, normalize_columns
from jd_turnover.processing.turnover import process
from jd_turnover.output.reporter import to_excel_bytes

app = FastAPI(title="京东自营周转数据处理")

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- 密码认证中间件 ---
_SKIP_AUTH = ACCESS_PASSWORD == ""

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if _SKIP_AUTH or request.url.path == "/health":
            return await call_next(request)

        token = request.cookies.get("jd_token", "")
        if token and token == _gen_token():
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                import base64
                decoded = base64.b64decode(auth[6:]).decode()
                user, pwd = decoded.split(":", 1)
                if user == "admin" and pwd == ACCESS_PASSWORD:
                    resp = await call_next(request)
                    resp.set_cookie("jd_token", _gen_token(), httponly=True, max_age=86400)
                    return resp
            except Exception:
                pass

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="JD Turnover"'},
            content="Authentication required. Please refresh and enter password.",
        )

def _gen_token():
    return secrets.token_hex(16)

app.add_middleware(AuthMiddleware)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    template = _jinja_env.get_template("index.html")
    return HTMLResponse(template.render(request=request))


@app.post("/upload")
async def upload_and_process(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"ok": False, "error": f"不支持的文件格式: {ext}, 仅支持 {ALLOWED_EXTENSIONS}"}

    contents = await file.read()
    size_mb = len(contents) / 1024 / 1024
    if size_mb > MAX_UPLOAD_SIZE_MB:
        return {"ok": False, "error": f"文件大小 {size_mb:.1f}MB 超过限制 {MAX_UPLOAD_SIZE_MB}MB"}

    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(contents)
    logger.info(f"文件上传成功: {file.filename} ({size_mb:.1f}MB)")

    try:
        df = load_file(save_path)
        df = drop_empty_rows(df)
        df = normalize_columns(df)
        df_raw, df_total, df_order = process(df)

        preview_data = df_total.head(100).to_dict(orient="records")
        columns = df_total.columns.tolist()

        return {
            "ok": True,
            "filename": file.filename,
            "rows": len(df_total),
            "columns": columns,
            "preview": preview_data,
            "order_count": len(df_order),
            "raw_count": len(df_raw),
        }
    except Exception as e:
        logger.exception("处理文件失败")
        return {"ok": False, "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/download")
async def download_result(request: Request):
    data = await request.json()
    filename = data.get("filename", "")

    save_path = UPLOAD_DIR / filename
    if not save_path.exists():
        return {"ok": False, "error": "文件不存在, 请重新上传"}

    try:
        df = load_file(save_path)
        df = drop_empty_rows(df)
        df = normalize_columns(df)
        df_raw, df_total, df_order = process(df)

        excel_bytes = to_excel_bytes(df_raw, df_total, df_order)

        download_name = f"京东自营周转匹配表_{Path(filename).stem}.xlsx"
        encoded_name = quote(download_name)
        return Response(
            content=excel_bytes.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
        )
    except Exception as e:
        logger.exception("下载处理失败")
        return {"ok": False, "error": str(e)}
