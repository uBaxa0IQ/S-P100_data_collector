from datetime import datetime, timedelta
import yfinance as yf
from sqlalchemy.orm import Session
from . import crud
import pandas as pd

def get_daily_data(db: Session, ticker: str):
    """
    Загружает дневные данные, используя кэширование в БД.
    """
    end_date = datetime.now()
    start_date_required = end_date - timedelta(days=365) # Required history length

    last_date_in_db = crud.get_last_daily_data_date(db, ticker)

    if last_date_in_db:
        # Data exists, check if we need to update
        if last_date_in_db.date() < end_date.date():
            start_date_download = last_date_in_db + timedelta(days=1)
            download_and_store_data(db, ticker, start_date_download, end_date)
    else:
        # No data in DB, download full history
        download_and_store_data(db, ticker, start_date_required, end_date)

    # Fetch all required data from DB
    data_from_db = crud.get_daily_data_by_ticker(db, ticker, start_date_required)
    
    if not data_from_db:
        return pd.DataFrame() # Return empty dataframe if no data

    # Convert to pandas DataFrame
    df = pd.DataFrame([
        {
            "date": item.date,
            "open": item.open,
            "high": item.high,
            "low": item.low,
            "close": item.close,
            "volume": item.volume
        }
        for item in data_from_db
    ])
    df.set_index('date', inplace=True)
    return df


def download_and_store_data(db: Session, ticker: str, start_date: datetime, end_date: datetime):
    """
    Скачивает данные из yfinance и сохраняет их в БД.
    """
    df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
    
    if df.empty:
        return

    # Handle multi-level columns if yfinance returns them for a single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(0)

    # Prepare data for bulk insert
    data_to_insert = []
    for index, row in df.iterrows():
        data_to_insert.append({
            "ticker": ticker,
            "date": index.to_pydatetime(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"])
        })
    
    crud.bulk_insert_daily_data(db, data_to_insert)
