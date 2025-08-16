from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from typing import List


class StockData(BaseModel):
    id: int
    ticker: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    # Pydantic v2: enable ORM mode
    model_config = ConfigDict(from_attributes=True)


class MarketRegime(BaseModel):
    ticker: str
    regime: str


class AllMarketRegimes(BaseModel):
    regimes: dict[str, str]


class TickersByRegime(BaseModel):
    regime: str
    tickers: List[str]


