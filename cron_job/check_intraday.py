import pandas as pd
import yfinance as yf


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


