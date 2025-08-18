from enum import IntEnum


class MarketRegime(IntEnum):
    NO_DATA = 0
    UPTREND = 1
    DOWNTREND = 2
    SQUEEZE = 3
    SIDEWAYS = 4
