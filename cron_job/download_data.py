import logging
import os
import sys
from datetime import timezone

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Ensure imports work both when executed as a module and as a script
try:
    from api.database import SessionLocal, engine
    from api import models
except ModuleNotFoundError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from api.database import SessionLocal, engine
    from api import models

from .tickers import SNP_100_TICKERS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def ensure_db_schema():
    models.Base.metadata.create_all(bind=engine)


def download_ticker_intraday(ticker: str, include_prepost: bool = True) -> pd.DataFrame:
    df = yf.download(
        tickers=ticker,
        period="1d",
        interval="1m",
        auto_adjust=False,
        prepost=include_prepost,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    # Normalize columns and timestamps (flatten possible MultiIndex columns)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]).lower() for col in df.columns]
    else:
        normalized_cols = []
        for col in df.columns:
            if isinstance(col, tuple):
                normalized_cols.append(str(col[0]).lower())
            else:
                normalized_cols.append(str(col).lower())
        df.columns = normalized_cols
    # Ensure timezone-aware UTC timestamps
    idx = pd.to_datetime(df.index, utc=True)
    df.index = idx
    return df


def upsert_stock_data(db: Session, ticker: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    if "close" not in df.columns:
        logger.warning("No 'close' column for ticker %s, skipping upsert.", ticker)
        return 0

    # Create a copy to avoid SettingWithCopyWarning and clean data
    df_clean = df.copy()

    # Ensure other columns exist, using 'close' as a fallback for OHLC.
    for col in ("open", "high", "low"):
        if col not in df_clean.columns:
            df_clean[col] = df_clean["close"]
    if "volume" not in df_clean.columns:
        df_clean["volume"] = 0

    # Drop rows with missing 'close' and fill other NaNs
    df_clean.dropna(subset=["close"], inplace=True)
    for col in ("open", "high", "low"):
        df_clean[col] = df_clean[col].fillna(df_clean["close"])
    df_clean["volume"] = df_clean["volume"].fillna(0)

    # Cast volume to integer
    df_clean["volume"] = df_clean["volume"].astype(int)

    if df_clean.empty:
        logger.info("No valid rows for %s after cleaning.", ticker)
        return 0

    rows = []
    for ts, row in df_clean.iterrows():
        ts_dt = ts.to_pydatetime()
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        rows.append({
            "ticker": ticker,
            "timestamp": ts_dt,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"]),
        })

    if not rows:
        return 0

    try:
        # Use RETURNING to get accurate count of inserted rows in PostgreSQL
        stmt = (
            insert(models.StockData)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["ticker", "timestamp"])
            .returning(models.StockData.id)
        )
        result = db.execute(stmt)
        inserted_ids = list(result.scalars().all())
        db.commit()
        return len(inserted_ids)
    except Exception:
        db.rollback()
        raise


def main():
    logger.info("Starting daily stock data download job")
    ensure_db_schema()

    with SessionLocal() as db:
        total_inserted = 0
        for ticker in SNP_100_TICKERS:
            try:
                logger.info("Downloading %s", ticker)
                df = download_ticker_intraday(ticker)
                if df.empty:
                    logger.warning("No data for %s", ticker)
                    continue
                inserted = upsert_stock_data(db, ticker, df)
                total_inserted += inserted
                logger.info("%s: upserted %s rows", ticker, inserted)
            except Exception as exc:
                logger.exception("Failed processing %s: %s", ticker, exc)

    logger.info("Job finished. Total new rows: %s", total_inserted)


if __name__ == "__main__":
    main()


