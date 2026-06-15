from datetime import datetime
from typing import Any

import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session
from yahooquery import Ticker as YQTicker
from yahooquery import search as yahoo_search

from app.services.cache import get_cached_json, set_cached_json

# Yahoo ETF/stock weight fields are often 0.08 for 8%; ratios (P/E) are factors, not percents.
_VALUATION_KEYS = frozenset(
    {
        "priceToEarnings",
        "priceToEarningsCat",
        "priceToBook",
        "priceToBookCat",
        "priceToSales",
        "priceToSalesCat",
        "priceToCashflow",
        "priceToCashflowCat",
        "medianMarketCap",
        "medianMarketCapCat",
        "threeYearEarningsGrowth",
        "threeYearEarningsGrowthCat",
    }
)
_VALUATION_LABELS = {
    "priceToEarnings": "KGV (P/E)",
    "priceToBook": "KBV (P/B)",
    "priceToSales": "KUV (P/S)",
    "priceToCashflow": "KCV (P/CF)",
    "medianMarketCap": "Median Marktkapitalisierung",
    "threeYearEarningsGrowth": "Gewinnwachstum (3J)",
    "trailingPE": "KGV (P/E)",
    "forwardPE": "KGV Forward",
    "priceToBook": "KBV (P/B)",
    "priceToSalesTrailing12Months": "KUV (P/S)",
}


def normalize_ticker(raw: str) -> str:
    """Return the ticker exactly as entered by the user (only trim whitespace). No exchange suffix, no ISIN mapping."""
    return (raw or "").strip()


def normalize_weight_pct(value: float | None) -> float | None:
    """Convert Yahoo decimal weights (0.08) to display percent (8.0). Leaves values already in percent."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not (v == v):  # NaN
        return None
    if 0 < abs(v) <= 1.0:
        return v * 100.0
    return v


def normalize_weight_map(data: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in data.items():
        if k in _VALUATION_KEYS:
            continue
        n = normalize_weight_pct(v)
        if n is not None:
            out[str(k)] = n
    return out


def _humanize_sector_key(key: str) -> str:
    mapping = {
        "realestate": "Immobilien",
        "technology": "Technologie",
        "financialservices": "Finanzdienstleistungen",
        "consumercyclical": "Zyklische Konsumgüter",
        "consumerdefensive": "Defensive Konsumgüter",
        "healthcare": "Gesundheitswesen",
        "utilities": "Versorger",
        "energy": "Energie",
        "industrials": "Industrie",
        "basicmaterials": "Grundstoffe",
        "communicationservices": "Kommunikation",
    }
    k = (key or "").strip().lower().replace(" ", "").replace("_", "")
    return mapping.get(k, key.replace("_", " ").title() if key else "Unknown")


def _parse_sector_weightings(raw: Any) -> dict[str, float]:
    """Parse yahooquery sectorWeightings list-of-dicts into labeled percent map."""
    out: dict[str, float] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            for k, v in item.items():
                n = normalize_weight_pct(v)
                if n is not None:
                    out[_humanize_sector_key(str(k))] = n
    elif isinstance(raw, dict):
        for k, v in raw.items():
            n = normalize_weight_pct(v)
            if n is not None:
                out[_humanize_sector_key(str(k))] = n
    return out


def _extract_etf_valuation_ratios(equity_holdings: Any) -> dict[str, float]:
    if not isinstance(equity_holdings, dict):
        return {}
    out: dict[str, float] = {}
    for key in ("priceToEarnings", "priceToBook", "priceToSales", "priceToCashflow"):
        val = equity_holdings.get(key)
        if val is None:
            continue
        try:
            f = float(val)
            if f == f and f > 0:
                label = _VALUATION_LABELS.get(key, key)
                out[label] = round(f, 2)
        except (TypeError, ValueError):
            continue
    return out


def search_instruments(term: str, limit: int = 10) -> list[dict]:
    if len(term.strip()) < 2:
        return []
    try:
        raw = yahoo_search(term)
    except Exception:
        return []
    quotes = (raw or {}).get("quotes", [])[:limit]
    return [
        {
            "symbol": q.get("symbol"),
            "shortname": q.get("shortname"),
            "exch_disp": q.get("exchDisp"),
            "quote_type": q.get("quoteType"),
        }
        for q in quotes
        if q.get("symbol")
    ]


def _flatten_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure JSON-serializable string column names (no MultiIndex tuples)."""
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [col[0] if isinstance(col, tuple) else str(col) for col in df.columns]
    elif hasattr(df.columns, "to_flat_index"):
        df = df.copy()
        df.columns = [str(col) for col in df.columns.to_flat_index()]
    else:
        df = df.copy()
        df.columns = [str(col) for col in df.columns]
    return df


def _flatten_close_column(frame: pd.DataFrame) -> pd.DataFrame:
    """yfinance may return a MultiIndex column (e.g. ('Close', 'AAPL')); normalize to Date + Close."""
    if frame.empty:
        return frame

    frame = _flatten_column_names(frame.reset_index())

    date_col = None
    for name in ("Date", "Datetime", "index"):
        if name in frame.columns:
            date_col = name
            break
    if date_col is None:
        date_col = frame.columns[0]

    close_col = None
    for name in ("Close", "Adj Close"):
        if name in frame.columns:
            close_col = name
            break
    if close_col is None:
        return pd.DataFrame()

    out = frame[[date_col, close_col]].copy()
    out.columns = ["Date", "Close"]
    return out


def get_quote(db: Session, symbol: str) -> dict:
    cache_key = f"quote:{symbol}"
    cached = get_cached_json(db, cache_key, max_age_minutes=5)
    if cached:
        return cached

    ticker = yf.Ticker(symbol)
    info = ticker.fast_info
    payload = {
        "symbol": symbol,
        "price": float(info.get("lastPrice") or 0),
        "prev_close": float(info.get("previousClose") or info.get("lastPrice") or 0),
        "currency": info.get("currency") or "EUR",
        "ts": datetime.utcnow().isoformat(),
    }
    set_cached_json(db, cache_key, payload)
    return payload


def get_fundamentals(db: Session, symbol: str) -> dict[str, Any]:
    """Sector / industry from yfinance `info`, with safe fallbacks (never raises)."""
    cache_key = f"fundamentals:{symbol}"
    cached = get_cached_json(db, cache_key, max_age_minutes=360)
    if cached:
        return cached

    sector = "Unknown"
    industry = "Unknown"
    quote_type: str | None = None
    long_name: str | None = None
    valuation_ratios: dict[str, float] = {}

    try:
        t = yf.Ticker(symbol)
        info = t.info
        if isinstance(info, dict) and info:
            quote_type = info.get("quoteType")
            long_name = info.get("longName") or info.get("shortName")
            raw_sector = info.get("sector") or info.get("category")
            raw_industry = info.get("industry")
            if raw_sector:
                sector = str(raw_sector)
            if raw_industry:
                industry = str(raw_industry)
            if (not raw_sector or sector == "None") and quote_type == "ETF":
                sector = "ETF"
            if (not raw_industry or industry == "None") and quote_type == "ETF":
                industry = "ETF"
            if quote_type == "INDEX":
                sector = "Index"
                industry = industry if industry and industry != "Unknown" else "Index"
            for src_key, label in (
                ("trailingPE", "KGV (P/E)"),
                ("forwardPE", "KGV Forward"),
                ("priceToBook", "KBV (P/B)"),
                ("priceToSalesTrailing12Months", "KUV (P/S)"),
            ):
                val = info.get(src_key)
                if val is not None:
                    try:
                        f = float(val)
                        if f == f and f > 0:
                            valuation_ratios[label] = round(f, 2)
                    except (TypeError, ValueError):
                        pass
    except Exception:
        pass

    for label, val in (("sector", sector), ("industry", industry)):
        if val is None or str(val).strip() == "" or str(val).lower() == "none":
            if label == "sector":
                sector = "Unknown"
            else:
                industry = "Unknown"

    payload = {
        "sector": sector,
        "industry": industry,
        "quote_type": quote_type,
        "long_name": long_name,
        "valuation_ratios": valuation_ratios,
    }
    set_cached_json(db, cache_key, payload)
    return payload


def get_symbol_sector(db: Session, symbol: str) -> str:
    """Primary sector label for risk/stress (ETF: largest sector weight)."""
    fund = get_fundamentals(db, symbol)
    sector = fund.get("sector") or "Unknown"
    if sector not in ("Unknown", "ETF", "Index", "Fund"):
        return sector
    sectors, _, _ = safe_etf_fund_breakdown(symbol)
    if sectors:
        return max(sectors.items(), key=lambda x: x[1])[0]
    return sector


def safe_etf_fund_breakdown(
    symbol: str,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """ETF sector weights, bond ratings, top holdings (%), valuation ratios; never raises."""
    sectors: dict[str, float] = {}
    countries: dict[str, float] = {}
    top_holdings: dict[str, float] = {}
    valuation_ratios: dict[str, float] = {}

    def _to_float_map(obj: Any, as_percent: bool = True) -> dict[str, float]:
        if not isinstance(obj, dict):
            return {}
        out: dict[str, float] = {}
        for k, v in obj.items():
            if v is None or k is None or str(k) in _VALUATION_KEYS:
                continue
            try:
                f = float(v)
                out[str(k)] = normalize_weight_pct(f) if as_percent else f
            except (TypeError, ValueError):
                continue
        return {k: v for k, v in out.items() if v is not None}

    try:
        yq = YQTicker(symbol)
        raw = getattr(yq, "fund_holding_info", None)
        if not isinstance(raw, dict):
            return sectors, countries, top_holdings, valuation_ratios
        fund_data = raw.get(symbol)
        if not isinstance(fund_data, dict):
            fund_data = {}

        sectors = _parse_sector_weightings(fund_data.get("sectorWeightings"))
        valuation_ratios = _extract_etf_valuation_ratios(fund_data.get("equityHoldings"))
        countries = normalize_weight_map(_to_float_map(fund_data.get("bondRatings")))
        holdings_raw = fund_data.get("holdings")
        if isinstance(holdings_raw, list):
            for row in holdings_raw:
                if not isinstance(row, dict):
                    continue
                name = row.get("holdingName") or row.get("symbol") or "Holding"
                pct = row.get("holdingPercent") or row.get("pctOfPortfolio")
                try:
                    if pct is not None:
                        n = normalize_weight_pct(float(pct))
                        if n is not None:
                            top_holdings[str(name)] = n
                except (TypeError, ValueError):
                    continue
        elif isinstance(holdings_raw, dict):
            top_holdings = normalize_weight_map(_to_float_map(holdings_raw))
    except Exception:
        pass

    return sectors, countries, top_holdings, valuation_ratios


def get_history(db: Session, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    cache_key = f"history:{symbol}:{period}:{interval}"
    cached = get_cached_json(db, cache_key, max_age_minutes=60)
    if cached:
        return pd.DataFrame(cached)

    try:
        frame = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
    except Exception:
        return pd.DataFrame()

    if frame is None or frame.empty:
        return pd.DataFrame()

    normalized = _flatten_close_column(frame)
    if normalized.empty:
        return pd.DataFrame()

    normalized = _flatten_column_names(normalized)
    normalized["Date"] = normalized["Date"].astype(str)
    normalized["Close"] = pd.to_numeric(normalized["Close"], errors="coerce")

    cache_payload = normalized.to_dict(orient="list")
    set_cached_json(db, cache_key, cache_payload)
    return normalized
