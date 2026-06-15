"""Build position detail responses (quotes, history, fundamentals, ETF structure)."""

from app.schemas import PositionDetail, PricePoint, StructureAnalysis
from app.services.market_data import (
    get_fundamentals,
    get_history,
    get_quote,
    safe_etf_fund_breakdown,
)


def build_position_detail(db, ticker: str, period: str) -> PositionDetail:
    quote = get_quote(db, ticker)
    history_df = get_history(db, ticker, period=period)
    history: list[PricePoint] = []
    if not history_df.empty:
        for _, row in history_df.iterrows():
            try:
                history.append(PricePoint(date=str(row["Date"]), close=float(row["Close"])))
            except (TypeError, ValueError, KeyError):
                continue

    fund = get_fundamentals(db, ticker)
    sector_label = fund.get("sector") or "Unknown"
    industry_label = fund.get("industry") or "Unknown"
    quote_type = (fund.get("quote_type") or "") or ""

    if sector_label == "Unknown":
        qt = quote_type.upper()
        if qt == "ETF":
            sector_label = "ETF"
        elif qt in ("INDEX", "MUTUALFUND"):
            sector_label = "Index" if qt == "INDEX" else "Fund"

    sectors_alloc, countries_alloc, top_holdings, etf_ratios = safe_etf_fund_breakdown(ticker)
    valuation_ratios = dict(fund.get("valuation_ratios") or {})
    valuation_ratios.update(etf_ratios)

    if not sectors_alloc:
        if sector_label not in ("Unknown", "ETF", "Index", "Fund"):
            sectors_alloc = {sector_label: 100.0}
        elif sector_label == "ETF":
            sectors_alloc = {"ETF": 100.0}
        elif sector_label == "Index":
            sectors_alloc = {"Index": 100.0}
        else:
            sectors_alloc = {"Unknown": 100.0}

    if not countries_alloc:
        countries_alloc = {"N/A": 100.0}

    if not top_holdings:
        top_holdings = {ticker: 100.0}

    structure = StructureAnalysis(
        sector=sector_label,
        industry=industry_label,
        sectors=sectors_alloc,
        countries=countries_alloc,
        top_holdings=top_holdings,
        valuation_ratios=valuation_ratios,
    )

    return PositionDetail(
        ticker=ticker,
        latest_price=float(quote.get("price") or 0.0),
        history=history,
        structure=structure,
    )
