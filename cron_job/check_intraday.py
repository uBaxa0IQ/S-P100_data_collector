import os
import sys
import pandas as pd
import yfinance as yf

# Robust import of tickers whether run as module or script
try:
    from cron_job.tickers import SNP_100_TICKERS
except ModuleNotFoundError:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from cron_job.tickers import SNP_100_TICKERS


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


if __name__ == "__main__":
    print("Fetching AAPL 1m intraday...")
    data_frame = download_ticker_intraday("AAPL", include_prepost=True)
    if data_frame is None or data_frame.empty:
        print("No intraday data returned for AAPL")
    else:
        first_ts = data_frame.index[0]
        last_ts = data_frame.index[-1]
        print(f"First: {first_ts.isoformat()}")
        print(f"Last:  {last_ts.isoformat()}")
        print(data_frame)

    print("\nBatch fetching S&P 100 (1m, include pre/post) ...")
    total_rows = 0
    nonempty_tickers = 0
    for ticker in SNP_100_TICKERS:
        df = download_ticker_intraday(ticker, include_prepost=True)
        if df is None or df.empty:
            print(f"{ticker}: no data")
            continue
        nonempty_tickers += 1
        total_rows += len(df)
        first_ts = df.index[0]
        last_ts = df.index[-1]
        print(f"{ticker}: rows={len(df)} first={first_ts.isoformat()} last={last_ts.isoformat()}")

    print(f"\nSummary: tickers_with_data={nonempty_tickers} total_rows={total_rows}")


