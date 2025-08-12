import logging
from datetime import timezone

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

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


def download_ticker_intraday(ticker: str) -> pd.DataFrame:
    df = yf.download(
        tickers=ticker,
        period="1d",
        interval="1m",
        auto_adjust=False,
        prepost=False,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    # Normalize columns and timestamps
    df = df.rename(columns={c: c.lower() for c in df.columns})
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

        rows.append(
            {
                "ticker": ticker,
                "timestamp": ts_dt,
                "open": float(row.get("open")),
                "high": float(row.get("high")),
                "low": float(row.get("low")),
                "close": float(row.get("close")),
                "volume": int(row.get("volume", 0) or 0),
            }
        )

    stmt = insert(models.StockData).values(rows)
    do_nothing_stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "timestamp"])
    result = db.execute(do_nothing_stmt)
    db.commit()
    # result.rowcount may be -1 for some DBAPIs; return inserted count if available
    try:
        return result.rowcount or 0
    except Exception:
        return 0


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


