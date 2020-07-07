import pandas as pd

def moving_window(stock, short_window = 40 , long_window = 100):
    rolling = pd.DataFrame(index=stock.index)
    rolling['short_mavg'] = stock['close'].rolling(window=short_window, min_periods=1, center=False).mean()
    rolling['long_mavg'] = stock['close'].rolling(window=long_window, min_periods=1, center=False).mean()
    signals = rolling['short_mavg'][short_window:] > rolling['long_mavg'][short_window:]
    return signals[:1].values[0] 

