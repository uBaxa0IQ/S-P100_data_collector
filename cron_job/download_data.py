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
        df.columns = [str(col[-1]).lower() for col in df.columns]
    else:
        normalized_cols = []
        for col in df.columns:
            if isinstance(col, tuple):
                normalized_cols.append(str(col[-1]).lower())
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

    rows = []
    for ts, row in df.iterrows():
        # Convert to timezone-aware Python datetime in UTC
        ts_dt = ts.to_pydatetime()
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)

        open_val = row.get("open")
        high_val = row.get("high")
        low_val = row.get("low")
        close_val = row.get("close")
        volume_val = row.get("volume")

        # Skip rows with missing essential OHLC values
        if pd.isna(open_val) or pd.isna(high_val) or pd.isna(low_val) or pd.isna(close_val):
            continue

        volume_int = 0
        if not pd.isna(volume_val):
            try:
                volume_int = int(volume_val)
            except Exception:
                # In rare cases volume can be float/decimal; best effort cast
                try:
                    volume_int = int(float(volume_val))
                except Exception:
                    volume_int = 0

        rows.append(
            {
                "ticker": ticker,
                "timestamp": ts_dt,
                "open": float(open_val),
                "high": float(high_val),
                "low": float(low_val),
                "close": float(close_val),
                "volume": volume_int,
            }
        )

    if not rows:
        return 0

    try:
        stmt = insert(models.StockData).values(rows)
        do_nothing_stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "timestamp"])
        result = db.execute(do_nothing_stmt)
        db.commit()
        # result.rowcount may be -1 for some DBAPIs; return inserted count if available
        try:
            return result.rowcount or 0
        except Exception:
            return 0
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


