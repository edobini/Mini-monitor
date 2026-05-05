"""
cpi_loader.py  —  Loads CPI data from CPI_DATA folder
Structure:
    CPI_DATA/
        US/   CPIAUCNS.xlsx, CPILFESL.xlsx, CUSR0000SAC.xlsx,
               CUSR0000SAS.xlsx, CUUR0000SAH1.xlsx, CUSR0000SEHC.xlsx
        JP/   JPNCPIALLMINMEI.xlsx, JPNCPICORMINMEI.xlsx
        CH/   CHNCPIALLMINMEI.xlsx
        UK/   consumerpriceinflationdetailedreferencetables.xlsx
        EU/   ECB_Data_Portal_*.csv
        SW/   su-e-05_02_66.xlsx
"""

import os
import glob
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "CPI_DATA")


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _fred_series(folder: str, ticker: str) -> pd.Series:
    """Read a FRED xlsx (second sheet, cols: observation_date | value)."""
    path = os.path.join(BASE, folder, f"{ticker}.xlsx")
    if not os.path.exists(path):
        return pd.Series(dtype=float, name=ticker)
    df = pd.read_excel(path, sheet_name=1, header=0)
    df.columns = ["date", "value"]
    df["date"]  = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date").sort_index()["value"].rename(ticker)


def _yoy(series: pd.Series) -> pd.Series:
    return series.pct_change(12) * 100


def _trim(series: pd.Series, n: int = 60) -> pd.Series:
    return series.dropna().tail(n)


# ─────────────────────────────────────────────
#  US
# ─────────────────────────────────────────────

def load_us() -> dict:
    raw = {
        "Headline": _fred_series("US", "CPIAUCNS"),
        "Core":     _fred_series("US", "CPILFESL"),
        "Goods":    _fred_series("US", "CUSR0000SAC"),
        "Services": _fred_series("US", "CUSR0000SAS"),
        "Shelter":  _fred_series("US", "CUUR0000SAH1"),
        "OER":      _fred_series("US", "CUSR0000SEHC"),
    }
    return {k: _trim(_yoy(v)) for k, v in raw.items() if len(v) > 12}


# ─────────────────────────────────────────────
#  JAPAN  (Statistics Bureau — am01-1.xlsx)
#
#  Sheet "am01-1 (3)" = YoY % change (前年同月比)
#  Col 7  = date label (e.g. "2026年 1月", then "2", "3" ...)
#  Key columns (0-based):
#    8  = All items (Headline)
#    9  = All items, less fresh food (BoJ Core)
#   12  = All items, less fresh food and energy (Core-core)
#   13  = All items, less food & energy (Western-style core)
#   14  = Food
#   15  = Fresh food
#   86  = Energy
#   31  = Meals outside the home (services proxy)
#   39  = Fuel, light & water charges
# ─────────────────────────────────────────────

_JP_COLS = {
    "Headline":              8,
    "Core (ex fresh food)":  9,
    "Core-core (ex FF&E)":  12,
    "Food":                 14,
    "Fresh Food":           15,
    "Energy":               86,
    "Meals Out":            31,
    "Fuel & Light":         39,
}

def _jp_parse_dates(date_col: pd.Series) -> pd.DatetimeIndex:
    """Parse Japanese date labels like '2026年 1月', '2  ', '3  ' ..."""
    dates = []
    current_year, current_month = None, None
    for raw in date_col:
        s = str(raw).strip()
        if "年" in s and "月" in s:
            # Full label e.g. "2026年 1月"
            try:
                s_clean = s.replace(" ", "")
                year  = int(s_clean.split("年")[0])
                month = int(s_clean.split("年")[1].replace("月",""))
                current_year, current_month = year, month
            except Exception:
                dates.append(pd.NaT)
                continue
        elif s and s.replace(" ","").isdigit():
            # Month-only label e.g. "2  " or "3"
            current_month = int(s.replace(" ",""))
        else:
            dates.append(pd.NaT)
            continue
        if current_year and current_month:
            dates.append(pd.Timestamp(year=current_year, month=current_month, day=1))
        else:
            dates.append(pd.NaT)
    return dates


def load_japan() -> dict:
    # Try new file first, fall back to FRED tickers
    path = os.path.join(BASE, "JP", "am01-1.xlsx")
    if not os.path.exists(path):
        # Fallback to FRED
        raw = {
            "Headline":          _fred_series("JP", "JPNCPIALLMINMEI"),
            "Core (ex FF)":      _fred_series("JP", "JPNCPICORMINMEI"),
        }
        return {k: _trim(_yoy(v)) for k, v in raw.items() if len(v) > 12}

    # Read YoY sheet (sheet index 2 = "am01-1 (3)")
    df = pd.read_excel(path, sheet_name=2, header=None)

    # Data rows start at row 14, skip last 4 footer rows
    data = df.iloc[14:-4, :].copy()
    dates = _jp_parse_dates(data.iloc[:, 7].values)

    result = {}
    for label, col in _JP_COLS.items():
        if col >= data.shape[1]:
            continue
        vals = pd.to_numeric(data.iloc[:, col].values, errors="coerce")
        s = pd.Series(vals, index=dates).dropna()
        s = s[s.index.notna()].sort_index()
        if len(s) > 0:
            result[label] = _trim(s)

    return result


# ─────────────────────────────────────────────
#  CHINA
# ─────────────────────────────────────────────

def load_china() -> dict:
    raw = {
        "Headline": _fred_series("CH", "CHNCPIALLMINMEI"),
    }
    return {k: _trim(_yoy(v)) for k, v in raw.items() if len(v) > 12}


# ─────────────────────────────────────────────
#  EU  (ECB CSV — already YoY %)
# ─────────────────────────────────────────────

_EU_COL_MAP = {
    "Headline": "000000",
    "Core":     "XEF000",
    "Food":     "FOOD00",
    "Energy":   "NRGY00",
    "Goods":    "IGXE00",
    "Services": "SERV00",
}

def load_eu() -> dict:
    folder = os.path.join(BASE, "EU")
    files  = glob.glob(os.path.join(folder, "ECB Data Portal_20260425143045.csv"))
    if not files:
        return {}
    df = pd.read_csv(sorted(files)[-1])
    df["date"] = pd.to_datetime(df["DATE"])
    df = df.set_index("date").sort_index()
    result = {}
    for label, key in _EU_COL_MAP.items():
        col = next((c for c in df.columns if key in c), None)
        if col:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            result[label] = _trim(s)
    return result


# ─────────────────────────────────────────────
#  UK  (ONS xlsx)
# ─────────────────────────────────────────────
#
#  Table 1: 3 years of CPIH & CPI headline YoY — col 1=date label,
#           col 3=CPIH YoY, col 5=CPI YoY  (rows 14-50)
#
#  Table 3: last 9 months of YoY for components
#           Cols 15-23 = Jul25..Mar26 (12-month rate)
#           Rows: 10=Headline,24=Goods,25=Services,26=Core,11=Food,14=Energy

_UK_T3_ROWS = {
    "Goods":    24,
    "Services": 25,
    "Core":     26,
    "Food":     11,
    "Energy":   14,
}

# Column indices in Table 3 that contain YoY% (positions 15-23, relative to col 0)
_UK_YOY_COLS = list(range(15, 24))


def _uk_parse_date(label: str, prev_year: int) -> pd.Timestamp | None:
    """Parse ONS date labels like 'Mar 2023', 'Apr', 'May' ..."""
    label = str(label).strip()
    if not label or label == "nan":
        return None
    parts = label.split()
    if len(parts) == 2:
        try:
            return pd.to_datetime(f"{parts[0]} {parts[1]}", format="%b %Y")
        except Exception:
            return None
    elif len(parts) == 1:
        # month only — use prev_year (year carries over until next "Mon YYYY")
        try:
            return pd.to_datetime(f"{parts[0]} {prev_year}", format="%b %Y")
        except Exception:
            return None
    return None


def load_uk() -> dict:
    path = os.path.join(BASE, "UK",
                        "consumerpriceinflationdetailedreferencetables.xlsx")
    if not os.path.exists(path):
        return {}

    # ── Headline from Table 1 (36 months) ──
    t1   = pd.read_excel(path, sheet_name="Table 1", header=None)
    dates, values = [], []
    current_year  = None
    for i in range(14, t1.shape[0]):
        date_label = str(t1.iloc[i, 1]).strip()
        val        = t1.iloc[i, 5]           # CPI YoY col
        if date_label == "nan" or pd.isna(val):
            continue
        parts = date_label.split()
        if len(parts) == 2:
            current_year = int(parts[1])
        if current_year is None:
            continue
        ts = _uk_parse_date(date_label, current_year)
        if ts:
            dates.append(ts)
            values.append(float(val))

    result = {}
    if dates:
        s = pd.Series(values, index=dates).sort_index().dropna()
        result["Headline"] = _trim(s)

    # ── Components from Table 3 (9 months) ──
    t3 = pd.read_excel(path, sheet_name="Table 3", header=None)

    # Build date index for YoY columns (cols 15-23)
    years_row  = t3.iloc[7, :]
    months_row = t3.iloc[8, :]
    comp_dates = []
    for col in _UK_YOY_COLS:
        y = years_row.iloc[col]
        m = months_row.iloc[col]
        if pd.isna(y) or pd.isna(m):
            comp_dates.append(None)
            continue
        try:
            comp_dates.append(pd.to_datetime(f"{str(m).strip()} {int(y)}",
                                              format="%b %Y"))
        except Exception:
            comp_dates.append(None)

    for label, row_i in _UK_T3_ROWS.items():
        pairs = []
        for col, dt in zip(_UK_YOY_COLS, comp_dates):
            if dt is None:
                continue
            val = t3.iloc[row_i, col]
            if pd.notna(val):
                try:
                    pairs.append((dt, float(val)))
                except (ValueError, TypeError):
                    pass
        if pairs:
            idx  = [p[0] for p in pairs]
            vals = [p[1] for p in pairs]
            result[label] = pd.Series(vals, index=idx).sort_index().dropna()

    return result


# ─────────────────────────────────────────────
#  SWITZERLAND  (FSO xlsx — VAR_m-12 sheet, already YoY %)
# ─────────────────────────────────────────────

_SW_ROWS = {
    "Headline":         4,
    "Food":             5,
    "Housing & Energy": 190,
    "Energy":           218,
    "Household Goods":  242,
    "Transport":        322,
    "Restaurants":      490,
}

def load_switzerland() -> dict:
    path = os.path.join(BASE, "SW", "su-e-05.02.66.xlsx")
    if not os.path.exists(path):
        return {}

    df = pd.read_excel(path, sheet_name="VAR_m-12", header=None)

    # Date headers: row 3, starting col 15
    date_row = df.iloc[3, 15:].values
    dates = []
    for d in date_row:
        try:
            dates.append(pd.Timestamp(d))
        except Exception:
            dates.append(None)

    result = {}
    for label, row_i in _SW_ROWS.items():
        if row_i >= df.shape[0]:
            continue
        row_data = df.iloc[row_i, 15:].values
        pairs = [(d, v) for d, v in zip(dates, row_data)
                 if d is not None and pd.notna(v)]
        if not pairs:
            continue
        idx  = [p[0] for p in pairs]
        vals = pd.to_numeric([p[1] for p in pairs], errors="coerce")
        s    = pd.Series(vals, index=idx).sort_index().dropna()
        result[label] = _trim(s)

    return result


# ─────────────────────────────────────────────
#  MASTER LOADER
# ─────────────────────────────────────────────

LOADERS = {
    "US":          load_us,
    "Japan":       load_japan,
    "China":       load_china,
    "EU":          load_eu,
    "UK":          load_uk,
    "Switzerland": load_switzerland,
}

def load_all() -> dict:
    result = {}
    for country, fn in LOADERS.items():
        try:
            result[country] = fn()
        except Exception as e:
            result[country] = {"_error": str(e)}
    return result
