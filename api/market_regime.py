from sqlalchemy.orm import Session
import pandas_ta as ta
import numpy as np

from .data_loader import get_daily_data
from .enums import MarketRegime as Regime


def calculate_market_regime(ticker: str, db: Session) -> Regime:
    """
    Анализирует дневные данные и определяет режим рынка для акции.
    """
    df = get_daily_data(db, ticker)

    if df.empty or len(df) < 200:
        return Regime.NO_DATA

    # Рассчитываем индикаторы
    df.ta.sma(length=20, append=True)
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)
    df.ta.adx(length=14, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.bbands(length=20, std=2, append=True)

    # Убираем строки с NaN после расчета индикаторов
    df.dropna(inplace=True)

    if df.empty:
        return Regime.NO_DATA

    # Последняя строка с актуальными данными
    last = df.iloc[-1]
    
    # 1. Наклон SMA20
    sma20_series = df['SMA_20']
    if len(sma20_series) > 1:
        # простой наклон по последним 2 точкам
        slope20 = sma20_series.iloc[-1] - sma20_series.iloc[-2]
    else:
        slope20 = 0

    # 2. Порядок скользящих средних
    align = "смешанный"
    if last['SMA_20'] > last['SMA_50'] > last['SMA_200']:
        align = "быч"
    elif last['SMA_20'] < last['SMA_50'] < last['SMA_200']:
        align = "медв"

    # 3. ADX
    adx = last['ADX_14']
    
    # 4. ATR в процентах от цены
    atrp = last['ATRr_14'] / last['Close']

    # 5. Сжатие Боллинджера
    squeeze = last['BBB_20_2.0'] / 100 # BBB is already a percentage

    # 6. Процентный диапазон за 20 дней
    high20 = df['High'][-20:].max()
    low20 = df['Low'][-20:].min()
    rangePct = (high20 - low20) / last['Close']

    # Логика определения режима
    if adx > 25 and align == "быч" and slope20 > 0:
        return Regime.UPTREND
    if adx > 25 and align == "медв" and slope20 < 0:
        return Regime.DOWNTREND
    if squeeze < 0.04 and rangePct < 0.20:
        return Regime.SQUEEZE
    
    return Regime.SIDEWAYS
