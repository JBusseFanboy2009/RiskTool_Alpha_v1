from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Portfolio, Position, User
from app.schemas import PositionCreate, PositionDetail, PositionOut
from app.services.market_data import get_quote, normalize_ticker
from app.services.position_detail import build_position_detail

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionOut])
def list_positions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    positions = db.query(Position).filter(Position.user_id == current_user.id).all()
    result = []
    for pos in positions:
        quote = get_quote(db, pos.ticker)
        prev_close = quote["prev_close"] or quote["price"]
        day_change = ((quote["price"] - prev_close) / prev_close * 100) if prev_close else 0.0
        result.append(
            PositionOut(
                id=pos.id,
                ticker=pos.ticker,
                isin=pos.isin,
                instrument_name=pos.instrument_name,
                quantity=pos.quantity,
                buy_price=pos.buy_price,
                created_at=pos.created_at,
                current_price=quote["price"],
                day_change_pct=day_change,
            )
        )
    return result


@router.post("", response_model=PositionOut)
def create_position(payload: PositionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    symbol = normalize_ticker(payload.ticker)
    if not symbol:
        raise HTTPException(status_code=400, detail="Ticker is required")
    quote = get_quote(db, symbol)
    if quote["price"] <= 0:
        raise HTTPException(status_code=400, detail="Symbol not found or no market data")

    portfolio_id = payload.portfolio_id
    if portfolio_id is None:
        portfolio = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).first()
        if not portfolio:
            portfolio = Portfolio(user_id=current_user.id, name="Main Portfolio")
            db.add(portfolio)
            db.flush()
        portfolio_id = portfolio.id

    position = Position(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        ticker=symbol,
        isin=None,
        instrument_name=symbol,
        quantity=payload.quantity,
        buy_price=payload.buy_price,
        currency=quote.get("currency", "EUR"),
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    return PositionOut(
        id=position.id,
        ticker=position.ticker,
        isin=position.isin,
        instrument_name=position.instrument_name,
        quantity=position.quantity,
        buy_price=position.buy_price,
        created_at=position.created_at,
        current_price=quote["price"],
        day_change_pct=0.0,
    )


@router.delete("/{position_id}", status_code=204)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    position = (
        db.query(Position)
        .filter(Position.id == position_id, Position.user_id == current_user.id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(position)
    db.commit()


@router.get("/{position_id}/detail", response_model=PositionDetail)
def get_position_detail(
    position_id: int,
    period: str = Query("1y", pattern="^(1mo|6mo|1y|3y)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full detail for one saved position (avoids URL issues with tickers like DAX.DE)."""
    position = (
        db.query(Position)
        .filter(Position.id == position_id, Position.user_id == current_user.id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return build_position_detail(db, position.ticker, period)


@router.get("/{position_id}", response_model=PositionOut)
def get_position(position_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    position = (
        db.query(Position)
        .filter(Position.id == position_id, Position.user_id == current_user.id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    quote = get_quote(db, position.ticker)
    return PositionOut(
        id=position.id,
        ticker=position.ticker,
        isin=position.isin,
        instrument_name=position.instrument_name,
        quantity=position.quantity,
        buy_price=position.buy_price,
        created_at=position.created_at,
        current_price=quote["price"],
        day_change_pct=0.0,
    )
