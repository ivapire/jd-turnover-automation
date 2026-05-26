import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
LOG_FILE = PROJECT_ROOT / "process.log"

MAX_UPLOAD_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# 访问密码，可通过环境变量 JD_PASSWORD 覆盖。为空则不启用密码保护。
ACCESS_PASSWORD = os.environ.get("JD_PASSWORD", "")
