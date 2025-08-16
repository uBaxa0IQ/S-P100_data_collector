from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from .market_regime import calculate_market_regime
from cron_job.tickers import S_P_100_TICKERS

from . import crud, models, schemas
from .database import Base, engine, get_db
from sqlalchemy.orm import Session


app = FastAPI(title="Stock Data API", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)


@app.get("/status")
def get_status(db: Session = Depends(get_db)):
    last_ts = crud.get_last_update_timestamp(db)
    return {"last_update_timestamp": last_ts}


@app.get("/data/all", response_model=List[schemas.StockData])
def get_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    return crud.get_all_data(db, skip=skip, limit=limit)


@app.get("/data/{ticker}", response_model=List[schemas.StockData])
def get_by_ticker(ticker: str, db: Session = Depends(get_db)):
    ticker_norm = ticker.upper()
    data = crud.get_data_by_ticker(db, ticker=ticker_norm)
    return data


@app.get("/regime/all", response_model=schemas.AllMarketRegimes)
def get_all_regimes(db: Session = Depends(get_db)):
    regimes = {
        ticker: calculate_market_regime(ticker, db)
        for ticker in S_P_100_TICKERS
    }
    return {"regimes": regimes}


@app.get("/regime/by_regime/{regime_name}", response_model=schemas.TickersByRegime)
def get_tickers_by_regime(regime_name: str, db: Session = Depends(get_db)):
    all_regimes = {
        ticker: calculate_market_regime(ticker, db)
        for ticker in S_P_100_TICKERS
    }
    tickers = [
        ticker for ticker, regime in all_regimes.items() if regime == regime_name
    ]
    return {"regime": regime_name, "tickers": tickers}


@app.get("/regime/{ticker}", response_model=schemas.MarketRegime)
def get_regime_for_ticker(ticker: str, db: Session = Depends(get_db)):
    regime = calculate_market_regime(ticker.upper(), db)
    return {"ticker": ticker.upper(), "regime": regime}


