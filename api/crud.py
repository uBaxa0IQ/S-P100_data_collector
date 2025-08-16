from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, desc
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


def get_last_daily_data_date(db: Session, ticker: str) -> Optional[datetime]:
    stmt = (
        select(func.max(models.StockDataDaily.date))
        .where(models.StockDataDaily.ticker == ticker)
    )
    result = db.execute(stmt).scalar_one_or_none()
    return result


def get_daily_data_by_ticker(
    db: Session, ticker: str, start_date: datetime
) -> List[models.StockDataDaily]:
    stmt = (
        select(models.StockDataDaily)
        .where(models.StockDataDaily.ticker == ticker)
        .where(models.StockDataDaily.date >= start_date)
        .order_by(models.StockDataDaily.date.asc())
    )
    return list(db.scalars(stmt).all())


def bulk_insert_daily_data(db: Session, data: List[dict]):
    if not data:
        return
    
    # Using SQLAlchemy Core for bulk insert (more efficient)
    from sqlalchemy.dialects.postgresql import insert
    from .database import engine

    table = models.StockDataDaily.__table__
    
    stmt = insert(table).values(data)
    
    update_dict = {
        'open': stmt.excluded.open,
        'high': stmt.excluded.high,
        'low': stmt.excluded.low,
        'close': stmt.excluded.close,
        'volume': stmt.excluded.volume,
    }
    
    # On conflict, update existing rows
    stmt = stmt.on_conflict_do_update(
        index_elements=['ticker', 'date'],
        set_=update_dict,
    )
    
    with engine.connect() as connection:
        connection.execute(stmt)
        connection.commit()


