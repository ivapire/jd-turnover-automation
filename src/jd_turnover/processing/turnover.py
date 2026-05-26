"""京东自营周转补货计算模块。

v5 核心逻辑：
- 按(上级B配送中心名称, SKU)分组聚合
- 日销7+14 = 近7日/7×50% + 近14日/14×50%
- 补货数量 = floor(日销×30 - 总库存)
- 补货箱数 = ceil(max(补货数量, 0) / 箱规)
- 修正补货数量 = 补货箱数 × 箱规
"""

import re
import math

import pandas as pd
from loguru import logger

# ============================================================
# 内置SKU映射表（54条，硬编码锁死）
# ============================================================
SKU_MAPPING = {
    # 呼吸系列（8条）
    "100197258444": {"商品简称": "呼吸【纸尿裤】S码32片", "系列": "呼吸系列", "箱规": 17},
    "100197258445": {"商品简称": "呼吸【纸尿裤】M码28片", "系列": "呼吸系列", "箱规": 17},
    "100197258446": {"商品简称": "呼吸【纸尿裤】L码24片", "系列": "呼吸系列", "箱规": 17},
    "100197258447": {"商品简称": "呼吸【纸尿裤】XL码20片", "系列": "呼吸系列", "箱规": 17},
    "100197258448": {"商品简称": "呼吸【拉拉裤】L码20片", "系列": "呼吸系列", "箱规": 16},
    "100197258449": {"商品简称": "呼吸【拉拉裤】XL码18片", "系列": "呼吸系列", "箱规": 16},
    "100197258450": {"商品简称": "呼吸【拉拉裤】XXL码16片", "系列": "呼吸系列", "箱规": 16},
    "100197258451": {"商品简称": "呼吸【拉拉裤】XXXL码14片", "系列": "呼吸系列", "箱规": 16},
    # 清风系列（9条）
    "100173705539": {"商品简称": "清风【纸尿裤】NB码36片", "系列": "清风系列", "箱规": 8},
    "100173705540": {"商品简称": "清风【纸尿裤】S码32片", "系列": "清风系列", "箱规": 8},
    "100173705541": {"商品简称": "清风【纸尿裤】M码28片", "系列": "清风系列", "箱规": 8},
    "100173705542": {"商品简称": "清风【纸尿裤】L码24片", "系列": "清风系列", "箱规": 8},
    "100173705543": {"商品简称": "清风【纸尿裤】XL码20片", "系列": "清风系列", "箱规": 8},
    "100224890100": {"商品简称": "清风【拉拉裤】L码22片", "系列": "清风系列", "箱规": 4},
    "100224890101": {"商品简称": "清风【拉拉裤】XL码20片", "系列": "清风系列", "箱规": 4},
    "100224890102": {"商品简称": "清风【拉拉裤】XXL码18片", "系列": "清风系列", "箱规": 4},
    "100224890103": {"商品简称": "清风【拉拉裤】XXXL码16片", "系列": "清风系列", "箱规": 4},
    "100224890104": {"商品简称": "清风【拉拉裤】XXXXL码14片", "系列": "清风系列", "箱规": 4},
    # 蓝蓝裤系列（9条）
    "100167822231": {"商品简称": "蓝蓝裤【纸尿裤】NB码38片", "系列": "蓝蓝裤系列", "箱规": 12},
    "100167822232": {"商品简称": "蓝蓝裤【纸尿裤】S码34片", "系列": "蓝蓝裤系列", "箱规": 12},
    "100167822233": {"商品简称": "蓝蓝裤【纸尿裤】M码30片", "系列": "蓝蓝裤系列", "箱规": 12},
    "100167822234": {"商品简称": "蓝蓝裤【纸尿裤】L码26片", "系列": "蓝蓝裤系列", "箱规": 12},
    "100167822235": {"商品简称": "蓝蓝裤【纸尿裤】XL码22片", "系列": "蓝蓝裤系列", "箱规": 12},
    "100167822236": {"商品简称": "蓝蓝裤【拉拉裤】L码22片", "系列": "蓝蓝裤系列", "箱规": 10},
    "100167822237": {"商品简称": "蓝蓝裤【拉拉裤】XL码20片", "系列": "蓝蓝裤系列", "箱规": 10},
    "100167822238": {"商品简称": "蓝蓝裤【拉拉裤】XXL码18片", "系列": "蓝蓝裤系列", "箱规": 10},
    "100167822239": {"商品简称": "蓝蓝裤【拉拉裤】XXXL码16片", "系列": "蓝蓝裤系列", "箱规": 10},
    # 云柔系列（10条）
    "100155286195": {"商品简称": "云柔【纸尿裤】NB码40片", "系列": "云柔系列", "箱规": 14},
    "100155286196": {"商品简称": "云柔【纸尿裤】S码36片", "系列": "云柔系列", "箱规": 14},
    "100155286197": {"商品简称": "云柔【纸尿裤】M码32片", "系列": "云柔系列", "箱规": 14},
    "100155286198": {"商品简称": "云柔【纸尿裤】L码28片", "系列": "云柔系列", "箱规": 14},
    "100155286199": {"商品简称": "云柔【纸尿裤】XL码24片", "系列": "云柔系列", "箱规": 14},
    "100155286200": {"商品简称": "云柔【拉拉裤】L码24片", "系列": "云柔系列", "箱规": 12},
    "100155286201": {"商品简称": "云柔【拉拉裤】XL码22片", "系列": "云柔系列", "箱规": 12},
    "100155286202": {"商品简称": "云柔【拉拉裤】XXL码20片", "系列": "云柔系列", "箱规": 12},
    "100155286203": {"商品简称": "云柔【拉拉裤】XXXL码18片", "系列": "云柔系列", "箱规": 12},
    "100224890105": {"商品简称": "云柔【拉拉裤】XXXXL码16片", "系列": "云柔系列", "箱规": 12},
    # 超薄系列（2条）
    "100224890142": {"商品简称": "超薄【拉拉裤】L码26片", "系列": "超薄系列", "箱规": 6},
    "100224890143": {"商品简称": "超薄【拉拉裤】XL码24片", "系列": "超薄系列", "箱规": 6},
}

# ============================================================
# 固定参数
# ============================================================
TURNOVER_DAYS = 30

# 总表-分SKU 固定18列列名
TOTAL_SHEET_HEADERS = [
    "SKUID", "上级B配送中心名称", "配送中心", "系列", "商品简称",
    "码数排序", "箱规", "7天销售", "14天销售",
    "C仓库存", "B仓库存", "采购未到库",
    "日销7+14", "补货数量", "补货箱数", "修正补货数量",
    "实时周转天数", "周转天数要求",
]

# 平台采购下单表 固定4列列名
ORDER_SHEET_HEADERS = ["SKU", "采购需求数量", "配送中心", "商品全称"]

# ============================================================
# 列名别名配置
# ============================================================
REQUIRED_FIELDS = {
    "SKU": ["SKU", "sku", "Sku", "商品SKU", "sku编码", "SKU编码", "商品编码"],
    "C仓库存": ["可用库存", "库存件数", "C仓库存", "当前库存", "库存数量", "现货库存"],
    "B仓库存": ["B仓京东可用库存", "B仓库存", "B库存", "前置仓库存", "门店库存", "分仓库存"],
    "采购未到库": ["采购未到货", "在途", "在途库存", "采购在途", "在途数量"],
    "近7日出库": ["近7日出库商品件数", "近7日出库", "近7天出库", "7天出库", "近7日销量", "7天销量", "近7天销量"],
    "近14日出库": ["近14日出库商品件数", "近14日出库", "近14天出库", "14天出库", "近14日销量", "14天销量", "近14天销量"],
    "商品名称": ["商品名称", "品名", "商品全称", "商品名", "产品名称"],
    "上级B配送中心名称": ["上级B配送中心名称", "上级配送中心名称"],
    "配送中心": ["配送中心", "配送中心名称", "配送中心名称（正式）"],
}


def _clean(s: str) -> str:
    """清理字符串：全角转半角，去空白和标点，小写。"""
    s = str(s).strip()
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("【", "[").replace("】", "]")
    s = re.sub(r"[\s、。，]", "", s)
    return s.lower()


def _clean_sku(val) -> str:
    """规范化 SKU：去除浮点数 .0 后缀。"""
    s = str(val).strip()
    if s.endswith(".0") and len(s) > 2:
        s = s[:-2]
    return s


def match_columns(df: pd.DataFrame) -> dict[str, str]:
    """将 DataFrame 列名匹配到标准字段名，返回 {标准名: 实际列名}。"""
    col_map = {}
    missing = []
    df_cols = {_clean(c): c for c in df.columns}

    for std, aliases in REQUIRED_FIELDS.items():
        for alias in aliases:
            key = _clean(alias)
            if key in df_cols:
                col_map[std] = df_cols[key]
                break
        else:
            missing.append(f"  - {std}（支持别名：{', '.join(aliases)}）")

    if missing:
        raise ValueError(f"底表缺失必填字段：\n" + "\n".join(missing))

    logger.info(f"列名匹配完成, 匹配 {len(col_map)} 个字段")
    return col_map


def process(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    执行 v5 周转补货计算。

    返回 (底表新_df, 总表_df, 采购下单表_df)
    """
    # 1. 列名匹配
    col_map = match_columns(df)

    # 2. 按 (上级B配送中心名称, SKU) 分组聚合
    groups: dict[tuple[str, str], dict] = {}
    for _, row in df.iterrows():
        sku = _clean_sku(row.get(col_map["SKU"], ""))
        if not sku or sku == "nan":
            continue

        wh_b_raw = row.get(col_map["上级B配送中心名称"], "")
        wh_b = str(wh_b_raw).strip() if pd.notna(wh_b_raw) else ""
        dc_raw = row.get(col_map.get("配送中心", ""), "")
        dc = str(dc_raw).strip() if pd.notna(dc_raw) else ""

        key = (wh_b, sku)
        if key not in groups:
            groups[key] = {
                "配送中心": "",
                "7天销售": 0.0,
                "14天销售": 0.0,
                "C仓库存": 0.0,
                "B仓库存": 0.0,
                "采购未到库": 0.0,
            }

        g = groups[key]
        if not g["配送中心"] and dc and dc != "nan":
            g["配送中心"] = dc

        def _f(field: str) -> float:
            val = row.get(col_map.get(field, ""), 0)
            try:
                return float(val) if pd.notna(val) else 0.0
            except (ValueError, TypeError):
                return 0.0

        g["7天销售"] += _f("近7日出库")
        g["14天销售"] += _f("近14日出库")
        g["C仓库存"] += _f("C仓库存")
        g["B仓库存"] += _f("B仓库存")
        g["采购未到库"] += _f("采购未到库")

    logger.info(f"分组聚合完成, 共 {len(groups)} 组")

    # 3. 生成总表-分SKU 和 平台采购下单表
    total_rows = []
    order_rows = []

    for (wh_b, sku), g in groups.items():
        mapping = SKU_MAPPING.get(sku, {})
        goods_short = mapping.get("商品简称", "")
        series = mapping.get("系列", "")
        box_spec = mapping.get("箱规", 1)

        sales_7 = g["7天销售"]
        sales_14 = g["14天销售"]
        stock_c = g["C仓库存"]
        stock_b = g["B仓库存"]
        on_way = g["采购未到库"]
        dc = g["配送中心"]

        daily_sales = (sales_7 / 7.0 * 0.5) + (sales_14 / 14.0 * 0.5)
        if daily_sales <= 0:
            daily_sales = 0.001

        total_stock = stock_c + stock_b + on_way
        replenish_raw = daily_sales * TURNOVER_DAYS - total_stock
        replenish_num = max(0, math.floor(replenish_raw))
        replenish_box = math.ceil(replenish_num / box_spec) if replenish_num > 0 else 0
        final_replenish = replenish_box * box_spec
        turnover_days = round(total_stock / daily_sales, 2)

        total_rows.append({
            "SKUID": sku,
            "上级B配送中心名称": wh_b,
            "配送中心": dc,
            "系列": series,
            "商品简称": goods_short,
            "码数排序": "",
            "箱规": box_spec,
            "7天销售": sales_7,
            "14天销售": sales_14,
            "C仓库存": stock_c,
            "B仓库存": stock_b,
            "采购未到库": on_way,
            "日销7+14": round(daily_sales, 4),
            "补货数量": round(replenish_raw, 2),
            "补货箱数": replenish_box,
            "修正补货数量": final_replenish,
            "实时周转天数": turnover_days,
            "周转天数要求": TURNOVER_DAYS,
        })

        if final_replenish > 0:
            order_rows.append({
                "SKU": sku,
                "采购需求数量": final_replenish,
                "配送中心": dc if dc else wh_b,
                "商品全称": goods_short,
            })

    df_total = pd.DataFrame(total_rows, columns=TOTAL_SHEET_HEADERS) if total_rows else pd.DataFrame(columns=TOTAL_SHEET_HEADERS)
    df_order = pd.DataFrame(order_rows, columns=ORDER_SHEET_HEADERS) if order_rows else pd.DataFrame(columns=ORDER_SHEET_HEADERS)

    logger.info(f"总表-分SKU: {len(df_total)} 行, 平台采购下单表: {len(df_order)} 行")
    return df, df_total, df_order
