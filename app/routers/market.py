from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import InstrumentSuggestion
from app.services.market_data import search_instruments

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/search", response_model=list[InstrumentSuggestion])
def search_symbols(
    q: str = Query(..., min_length=2),
    _user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
):
    hits = search_instruments(q)
    return [InstrumentSuggestion(**item) for item in hits]
