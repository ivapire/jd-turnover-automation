"""数据清洗模块。"""

import pandas as pd
from loguru import logger


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.dropna(how="all").reset_index(drop=True)
    logger.info(f"移除全空行: {before - len(df)} 行")
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


def auto_convert_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df
