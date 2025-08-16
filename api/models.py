from sqlalchemy import Column, Integer, String, DateTime, Numeric, UniqueConstraint, Index
from .database import Base


class StockData(Base):
    __tablename__ = "stock_data"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    open = Column(Numeric(20, 6), nullable=False)
    high = Column(Numeric(20, 6), nullable=False)
    low = Column(Numeric(20, 6), nullable=False)
    close = Column(Numeric(20, 6), nullable=False)
    volume = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", name="uq_ticker_timestamp"),
        Index("ix_ticker_timestamp", "ticker", "timestamp"),
    )


class StockDataDaily(Base):
    __tablename__ = "stock_data_daily"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    date = Column(DateTime(timezone=True), index=True, nullable=False)
    open = Column(Numeric(20, 6), nullable=False)
    high = Column(Numeric(20, 6), nullable=False)
    low = Column(Numeric(20, 6), nullable=False)
    close = Column(Numeric(20, 6), nullable=False)
    volume = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_ticker_date"),
        Index("ix_ticker_date", "ticker", "date"),
    )


