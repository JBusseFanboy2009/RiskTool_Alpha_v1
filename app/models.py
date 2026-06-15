from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), default="Main Portfolio", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    ticker = Column(String(32), nullable=False, index=True)
    isin = Column(String(32), nullable=True, index=True)
    instrument_name = Column(String(255), nullable=True)
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    currency = Column(String(16), default="EUR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    portfolio = relationship("Portfolio", back_populates="positions")


class InstrumentMapping(Base):
    __tablename__ = "instrument_mappings"

    id = Column(Integer, primary_key=True, index=True)
    isin = Column(String(32), unique=True, nullable=False, index=True)
    ticker = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    exchange = Column(String(32), default="XETRA", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
