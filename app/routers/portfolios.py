from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Position, User
from app.schemas import AllocationSlice, PortfolioOverview
from app.services.market_data import get_quote

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=PortfolioOverview)
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    positions = db.query(Position).filter(Position.user_id == current_user.id).all()
    slices = []
    total = 0.0
    for pos in positions:
        quote = get_quote(db, pos.ticker)
        value = pos.quantity * quote["price"]
        total += value
        slices.append({"ticker": pos.ticker, "value": value})

    allocation = []
    for item in slices:
        weight = (item["value"] / total) if total else 0.0
        allocation.append(AllocationSlice(ticker=item["ticker"], value=item["value"], weight=weight))

    return PortfolioOverview(total_value=total, slices=allocation)
