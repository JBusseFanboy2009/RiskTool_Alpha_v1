from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class PositionCreate(BaseModel):
    ticker: str = Field(min_length=1, description="Yahoo Finance symbol exactly as entered, e.g. AAPL, SPY, VUSA.L")
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)
    portfolio_id: int | None = None


class PositionOut(BaseModel):
    id: int
    ticker: str
    isin: str | None
    instrument_name: str | None
    quantity: float
    buy_price: float
    created_at: datetime
    current_price: float | None = None
    day_change_pct: float | None = None

    class Config:
        from_attributes = True


class InstrumentSuggestion(BaseModel):
    symbol: str
    shortname: str | None = None
    exch_disp: str | None = None
    quote_type: str | None = None


class AllocationSlice(BaseModel):
    ticker: str
    value: float
    weight: float


class PortfolioOverview(BaseModel):
    total_value: float
    slices: list[AllocationSlice]


class PricePoint(BaseModel):
    date: str
    close: float


class StructureAnalysis(BaseModel):
    """Single-name classification plus optional ETF-style breakdowns."""

    sector: str = "Unknown"
    industry: str = "Unknown"
    sectors: dict[str, float] = Field(default_factory=dict)
    countries: dict[str, float] = Field(default_factory=dict)
    top_holdings: dict[str, float] = Field(default_factory=dict)
    valuation_ratios: dict[str, float] = Field(default_factory=dict)


class PositionDetail(BaseModel):
    ticker: str
    latest_price: float
    history: list[PricePoint]
    structure: StructureAnalysis


class RiskRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    confidence: float = 0.95
    scenario: str = "tech_crash"
    shock_intensity: float = Field(default=1.0, ge=0.1, le=3.0)
    global_shock: float | None = Field(default=None, ge=-0.9, le=0.0)


class RiskResponse(BaseModel):
    result: dict[str, Any]
