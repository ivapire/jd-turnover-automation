"""CSV / Excel 文件加载模块。"""

from pathlib import Path

import pandas as pd
from loguru import logger


def load_file(file_path: Path) -> pd.DataFrame:
    ext = file_path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    logger.info(f"加载文件: {file_path.name}, 行数: {len(df)}, 列数: {len(df.columns)}")
    return df
