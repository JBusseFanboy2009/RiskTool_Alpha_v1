"""Risk analytics — shared by API and Streamlit UI."""

from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.analytics.risk import (
    annualized_volatility,
    correlation_matrix,
    drawdown_series,
    returns_from_prices,
    var_cvar_historical,
)
from app.analytics.stress import STRESS_SCENARIOS, list_scenarios, sector_shock_for
from app.models import Position
from app.services.market_data import get_history, get_symbol_sector


def portfolio_symbols(db: Session, user_id: int) -> list[str]:
    rows = db.query(Position.ticker).filter(Position.user_id == user_id).distinct().all()
    return [x[0] for x in rows]


def symbol_returns(db: Session, symbols: list[str], period: str = "1y") -> dict:
    result = {}
    for symbol in symbols:
        history = get_history(db, symbol, period=period)
        if history.empty:
            continue
        result[symbol] = returns_from_prices(history.rename(columns={"Close": "Close"}))
    return result


def compute_risk_o_meter(db: Session, user_id: int, symbols: list[str] | None = None) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms)
    vols = [float(annualized_volatility(series)) for series in ret.values()]
    keys = list(ret.keys())
    score = float(min(100.0, (sum(vols) / len(vols) * 100) if vols else 0.0))
    components = {k: float(v) for k, v in zip(keys, vols)}
    total_vol = sum(vols) if vols else 0.0
    contributions = {k: float((v / total_vol) * 100) if total_vol else 0.0 for k, v in zip(keys, vols)}
    return {"score": score, "components": components, "contributions": contributions, "symbol_count": len(keys)}


def compute_volatility(db: Session, user_id: int, symbols: list[str] | None = None) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms)
    vol_map = {symbol: annualized_volatility(series) for symbol, series in ret.items()}
    return {"annualized": vol_map, "labels": list(vol_map.keys()), "values": [float(v) for v in vol_map.values()]}


def compute_correlation(db: Session, user_id: int, symbols: list[str] | None = None) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms)
    matrix = correlation_matrix(ret)
    labels = list(matrix.keys()) if matrix else []
    return {"matrix": matrix, "labels": labels}


def compute_drawdown(db: Session, user_id: int, symbols: list[str] | None = None) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms, period="3y")
    summary = {}
    series = {}
    for symbol, returns in ret.items():
        dd = drawdown_series(returns)
        summary[symbol] = dd["max_drawdown"]
        series[symbol] = {"dates": dd["dates"], "values": dd["values"]}
    return {"summary": summary, "series": series}


def _histogram(values, bins: int = 30) -> tuple[list[int], list[float]]:
    if len(values) == 0:
        return [], []
    counts, edges = np.histogram(values, bins=bins)
    return [int(c) for c in counts], [float(e) for e in edges]


def compute_var_cvar(db: Session, user_id: int, symbols: list[str] | None = None, confidence: float = 0.95) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms)
    result = {}
    for symbol, series in ret.items():
        var, cvar = var_cvar_historical(series, confidence=confidence)
        clean = series.dropna().values
        hist, bin_edges = _histogram(clean, bins=30)
        result[symbol] = {
            "var": var,
            "cvar": cvar,
            "confidence": confidence,
            "histogram": {"counts": hist, "edges": bin_edges},
        }
    return result


def compute_stress_test(
    db: Session,
    user_id: int,
    symbols: list[str] | None = None,
    scenario: str = "tech_crash",
    shock_intensity: float = 1.0,
    global_shock: float | None = None,
) -> dict:
    syms = symbols or portfolio_symbols(db, user_id)
    ret = symbol_returns(db, syms)
    scenario_id = scenario if scenario in STRESS_SCENARIOS else "tech_crash"
    cfg = STRESS_SCENARIOS[scenario_id]
    intensity = float(shock_intensity)
    simulation = {}
    for symbol, series in ret.items():
        sector = get_symbol_sector(db, symbol)
        shock = sector_shock_for(sector, scenario_id, intensity=intensity, global_shock=global_shock)
        base_return = float((1 + series).prod() - 1)
        shocked_return = float((1 + base_return) * (1 + shock) - 1)
        simulation[symbol] = {
            "base_return": base_return,
            "shocked_return": shocked_return,
            "sector": sector,
            "applied_shock": shock,
        }
    n = len(simulation)
    portfolio_base = sum(s["base_return"] for s in simulation.values()) / n if n else 0.0
    portfolio_shocked = sum(s["shocked_return"] for s in simulation.values()) / n if n else 0.0
    return {
        "scenario": scenario_id,
        "scenario_label": cfg["label"],
        "description": cfg["description"],
        "shock_intensity": intensity,
        "global_shock": global_shock,
        "portfolio_base_return": portfolio_base,
        "portfolio_shocked_return": portfolio_shocked,
        "simulation": simulation,
    }


def get_stress_scenarios() -> list[dict]:
    return list_scenarios()
