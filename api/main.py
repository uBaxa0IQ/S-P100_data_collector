from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query

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


