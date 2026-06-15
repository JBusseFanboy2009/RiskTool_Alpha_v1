import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import MarketDataCache


def get_cached_json(db: Session, symbol: str, max_age_minutes: int = 30):
    row = db.query(MarketDataCache).filter(MarketDataCache.symbol == symbol).first()
    if not row:
        return None
    if datetime.utcnow() - row.updated_at > timedelta(minutes=max_age_minutes):
        return None
    return json.loads(row.payload)


def set_cached_json(db: Session, symbol: str, payload: dict):
    row = db.query(MarketDataCache).filter(MarketDataCache.symbol == symbol).first()
    serialized = json.dumps(payload)
    if row:
        row.payload = serialized
        row.updated_at = datetime.utcnow()
    else:
        row = MarketDataCache(symbol=symbol, payload=serialized, updated_at=datetime.utcnow())
        db.add(row)
    db.commit()
