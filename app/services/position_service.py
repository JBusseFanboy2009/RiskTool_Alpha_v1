"""Position & portfolio operations — shared by API and Streamlit UI."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Portfolio, Position
from app.services.market_data import get_quote, normalize_ticker, search_instruments
from app.services.position_detail import build_position_detail


def list_positions_for_user(db: Session, user_id: int) -> list[dict]:
    positions = db.query(Position).filter(Position.user_id == user_id).all()
    result = []
    for pos in positions:
        quote = get_quote(db, pos.ticker)
        prev_close = quote["prev_close"] or quote["price"]
        day_change = ((quote["price"] - prev_close) / prev_close * 100) if prev_close else 0.0
        result.append(
            {
                "id": pos.id,
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "buy_price": pos.buy_price,
                "current_price": quote["price"],
                "day_change_pct": day_change,
                "value": pos.quantity * quote["price"],
            }
        )
    return result


def create_position(db: Session, user_id: int, ticker: str, quantity: float, buy_price: float) -> dict:
    symbol = normalize_ticker(ticker)
    if not symbol:
        raise ValueError("Ticker ist erforderlich")
    quote = get_quote(db, symbol)
    if quote["price"] <= 0:
        raise ValueError("Symbol nicht gefunden oder keine Marktdaten")

    portfolio = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=user_id, name="Main Portfolio")
        db.add(portfolio)
        db.flush()

    position = Position(
        user_id=user_id,
        portfolio_id=portfolio.id,
        ticker=symbol,
        instrument_name=symbol,
        quantity=quantity,
        buy_price=buy_price,
        currency=quote.get("currency", "EUR"),
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return {"id": position.id, "ticker": position.ticker}


def delete_position(db: Session, user_id: int, position_id: int) -> None:
    position = db.query(Position).filter(Position.id == position_id, Position.user_id == user_id).first()
    if not position:
        raise ValueError("Position nicht gefunden")
    db.delete(position)
    db.commit()


def portfolio_overview(db: Session, user_id: int) -> dict:
    positions = db.query(Position).filter(Position.user_id == user_id).all()
    slices = []
    total = 0.0
    for pos in positions:
        quote = get_quote(db, pos.ticker)
        value = pos.quantity * quote["price"]
        total += value
        slices.append({"ticker": pos.ticker, "value": value})
    for item in slices:
        item["weight"] = (item["value"] / total) if total else 0.0
    return {"total_value": total, "slices": slices}


def get_position_detail(db: Session, user_id: int, position_id: int, period: str = "1y"):
    position = db.query(Position).filter(Position.id == position_id, Position.user_id == user_id).first()
    if not position:
        raise ValueError("Position nicht gefunden")
    return build_position_detail(db, position.ticker, period)


def search_market(term: str) -> list[dict]:
    return search_instruments(term)
