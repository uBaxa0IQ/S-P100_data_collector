from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import models


def get_data_by_ticker(db: Session, ticker: str) -> List[models.StockData]:
    stmt = (
        select(models.StockData)
        .where(models.StockData.ticker == ticker)
        .order_by(models.StockData.timestamp.asc())
    )
    return list(db.scalars(stmt).all())


def get_all_data(db: Session, skip: int = 0, limit: int = 100) -> List[models.StockData]:
    stmt = select(models.StockData).order_by(models.StockData.timestamp.asc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_last_update_timestamp(db: Session) -> Optional[str]:
    stmt = select(func.max(models.StockData.timestamp))
    result = db.execute(stmt).scalar_one_or_none()
    # Return ISO string or None
    return result.isoformat() if result is not None else None


