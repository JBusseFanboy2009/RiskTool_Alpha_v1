from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.risk import (
    annualized_volatility,
    correlation_matrix,
    drawdown_series,
    returns_from_prices,
    var_cvar_historical,
)
from app.analytics.stress import STRESS_SCENARIOS, list_scenarios, sector_shock_for
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Position, User
from app.schemas import RiskRequest, RiskResponse
from app.services.market_data import get_history, get_symbol_sector

router = APIRouter(prefix="/risk", tags=["risk"])


def _portfolio_symbols(db: Session, user_id: int) -> list[str]:
    rows = db.query(Position.ticker).filter(Position.user_id == user_id).distinct().all()
    return [x[0] for x in rows]


def _symbol_returns(db: Session, symbols: list[str], period: str = "1y"):
    result = {}
    for symbol in symbols:
        history = get_history(db, symbol, period=period)
        if history.empty:
            continue
        result[symbol] = returns_from_prices(history.rename(columns={"Close": "Close"}))
    return result


@router.get("/portfolio-symbols")
def portfolio_symbols(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {"symbols": _portfolio_symbols(db, current_user.id)}


@router.get("/stress-scenarios")
def stress_scenarios():
    return {"scenarios": list_scenarios()}


@router.post("/risk-o-meter", response_model=RiskResponse)
def risk_o_meter(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols if payload.symbols else _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols)
    vols = [float(annualized_volatility(series)) for series in ret.values()]
    keys = list(ret.keys())
    score = float(min(100.0, (sum(vols) / len(vols) * 100) if vols else 0.0))
    components = {k: float(v) for k, v in zip(keys, vols)}
    total_vol = sum(vols) if vols else 0.0
    contributions = {
        k: float((v / total_vol) * 100) if total_vol else 0.0 for k, v in zip(keys, vols)
    }
    return RiskResponse(
        result={
            "score": score,
            "components": components,
            "contributions": contributions,
            "symbol_count": len(keys),
        }
    )


@router.post("/volatility", response_model=RiskResponse)
def volatility(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols or _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols)
    vol_map = {symbol: annualized_volatility(series) for symbol, series in ret.items()}
    return RiskResponse(
        result={
            "annualized": vol_map,
            "labels": list(vol_map.keys()),
            "values": [float(v) for v in vol_map.values()],
        }
    )


@router.post("/correlation", response_model=RiskResponse)
def correlation(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols or _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols)
    matrix = correlation_matrix(ret)
    labels = list(matrix.keys()) if matrix else []
    return RiskResponse(result={"matrix": matrix, "labels": labels})


@router.post("/max-drawdown", response_model=RiskResponse)
def max_drawdown(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols or _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols, period="3y")
    summary = {}
    series = {}
    for symbol, returns in ret.items():
        dd = drawdown_series(returns)
        summary[symbol] = dd["max_drawdown"]
        series[symbol] = {"dates": dd["dates"], "values": dd["values"]}
    return RiskResponse(result={"summary": summary, "series": series})


@router.post("/var-cvar", response_model=RiskResponse)
def var_cvar(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols or _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols)
    result = {}
    for symbol, series in ret.items():
        var, cvar = var_cvar_historical(series, confidence=payload.confidence)
        clean = series.dropna().values
        hist, bin_edges = _histogram(clean, bins=30)
        result[symbol] = {
            "var": var,
            "cvar": cvar,
            "confidence": payload.confidence,
            "histogram": {"counts": hist, "edges": bin_edges},
            "returns_sample": [float(x) for x in clean[-120:]],
        }
    return RiskResponse(result=result)


def _histogram(values, bins: int = 30) -> tuple[list[int], list[float]]:
    import numpy as np

    if len(values) == 0:
        return [], []
    counts, edges = np.histogram(values, bins=bins)
    return [int(c) for c in counts], [float(e) for e in edges]


@router.post("/stress-test", response_model=RiskResponse)
def stress_test(payload: RiskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbols = payload.symbols or _portfolio_symbols(db, current_user.id)
    ret = _symbol_returns(db, symbols)
    scenario_id = payload.scenario if payload.scenario in STRESS_SCENARIOS else "tech_crash"
    cfg = STRESS_SCENARIOS[scenario_id]
    intensity = float(payload.shock_intensity)
    simulation = {}
    for symbol, series in ret.items():
        sector = get_symbol_sector(db, symbol)
        shock = sector_shock_for(sector, scenario_id, intensity=intensity, global_shock=payload.global_shock)
        base_return = float((1 + series).prod() - 1)
        shocked_return = float((1 + base_return) * (1 + shock) - 1)
        simulation[symbol] = {
            "base_return": base_return,
            "shocked_return": shocked_return,
            "sector": sector,
            "applied_shock": shock,
        }
    portfolio_base = sum(s["base_return"] for s in simulation.values()) / len(simulation) if simulation else 0.0
    portfolio_shocked = sum(s["shocked_return"] for s in simulation.values()) / len(simulation) if simulation else 0.0
    return RiskResponse(
        result={
            "scenario": scenario_id,
            "scenario_label": cfg["label"],
            "description": cfg["description"],
            "shock_intensity": intensity,
            "global_shock": payload.global_shock,
            "portfolio_base_return": portfolio_base,
            "portfolio_shocked_return": portfolio_shocked,
            "simulation": simulation,
        }
    )
