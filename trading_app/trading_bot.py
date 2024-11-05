# trading_app/trading_bot.py

import ccxt
import talib
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import logging
from my_trading_bot import settings

# --- Logging Setup ---
logging.basicConfig(filename='trading_bot_backtest.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Bybit API Credentials ---
API_KEY = settings.API_KEY
API_SECRET = settings.API_SECRET

# --- Exchange Setup ---
exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Or 'spot'
    }
})

# --- Trading Parameters ---
SYMBOLS = [
    "SOL/USDT", "PEPE/USDT", "AVAX/USDT",
    "SUI/USDT", "OP/USDT", "APE/USDT", "SEI/USDT", "FTM/USDT", "TRX/USDT"
]

# Define BASE_ORDER_AMOUNT for each pair
BASE_ORDER_AMOUNTS = {
    "SOL/USDT": 0.08,
    "PEPE/USDT": 1000000,
    "AVAX/USDT": 0.3,
    # "ADA/USDT": 1.0,
    "SUI/USDT": 20.0,
    "OP/USDT": 0.3,
    "APE/USDT": 0.8,
    "SEI/USDT": 0.4,
    "FTM/USDT": 0.6,
    "TRX/USDT": 2.0,
}

TIMEFRAME = "15m"
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05

# --- Trading Logic Parameters ---
RSI_OVERBOUGHT = 65  # Decreased from 70
RSI_OVERSOLD = 35   # Increased from 30
EMA_PERIOD = 10      # Decreased from 20

# --- Backtesting Parameters ---
INITIAL_BALANCE = 5  # Starting balance for the backtest


# --- Helper Functions ---
def fetch_ohlcv_data(symbol, timeframe, limit=10000):
    """Fetches the last 10000 candlesticks from Bybit."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except ccxt.NetworkError as e:
        logging.error(f"Network error: {e}")
        return None
    except ccxt.ExchangeError as e:
        logging.error(f"Bybit API error: {e}")
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return None


def calculate_indicators(df):
    """Calculates technical indicators."""
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
        df['close'], fastperiod=12, slowperiod=26, signalperiod=9
    )
    df['ema_20'] = talib.EMA(df['close'], timeperiod=EMA_PERIOD)
    return df


def detect_candlestick_patterns(df):
    """Detects candlestick patterns."""
    df['engulfing'] = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    df['hammer'] = talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    df['shooting_star'] = talib.CDLSHOOTINGSTAR(df['open'], df['high'], df['low'], df['close'])
    df['doji'] = talib.CDLDOJI(df['open'], df['high'], df['low'], df['close'])
    # ... Add more patterns (morning star, evening star, etc.) ...
    return df


def generate_signals(df):
    """Generates trading signals with multiple confirmations."""
    df = calculate_indicators(df)
    df = detect_candlestick_patterns(df)
    df['signal'] = 0

    # --- Engulfing Pattern Logic ---
    df['signal'] = np.where(
        (df['engulfing'] > 0) &
        (df['rsi'] < RSI_OVERSOLD),
        1, df['signal']
    )
    df['signal'] = np.where(
        (df['engulfing'] < 0) &
        (df['rsi'] > RSI_OVERBOUGHT),
        -1, df['signal']
    )

    # --- Hammer and Shooting Star Logic ---
    df['signal'] = np.where(
        (df['hammer'] > 0) & (df['rsi'] < RSI_OVERSOLD),
        1, df['signal']
    )
    df['signal'] = np.where(
        (df['shooting_star'] < 0) & (df['rsi'] > RSI_OVERBOUGHT),
        -1, df['signal']
    )

    # --- Doji Pattern Logic ---
    df['signal'] = np.where(
        (df['doji'] != 0) & (df['rsi'] < RSI_OVERSOLD),
        1, df['signal']
    )
    df['signal'] = np.where(
        (df['doji'] != 0) & (df['rsi'] > RSI_OVERBOUGHT),
        -1, df['signal']
    )

    # ... Add logic for other patterns ...

    return df


def backtest_trade(symbol, signal, amount, current_price, entry_time, trades):
    """Simulates trade execution and records the trade with entry time."""
    order = {
        'symbol': symbol,
        'amount': amount,
        'entry_price': current_price,
        'side': 'long' if signal == 1 else 'short',
        'stop_loss': current_price * (1 - STOP_LOSS_PCT) if signal == 1 else current_price * (1 + STOP_LOSS_PCT),
        'take_profit': current_price * (1 + TAKE_PROFIT_PCT) if signal == 1 else current_price * (1 - TAKE_PROFIT_PCT),
        'entry_time': entry_time,
        'exit_price': None,
        'exit_time': None
    }
    trades.append(order)


def simulate_trade_execution(balance, trades, df):
    """Simulates stop-loss and take-profit execution."""
    last_price = df['close'].iloc[-1]  # Get the last closing price
    last_time = df['timestamp'].iloc[-1]  # Get the last timestamp

    for trade in trades:
        if trade['exit_price'] is None:
            for i in range(trades.index(trade) + 1, len(df)):
                current_price = df['close'].iloc[i]
                current_time = df['timestamp'].iloc[i]
                if trade['side'] == 'long':
                    if current_price <= trade['stop_loss'] or current_price >= trade['take_profit']:
                        trade['exit_price'] = current_price
                        trade['exit_time'] = current_time
                        balance += (trade['exit_price'] - trade['entry_price']) * trade['amount']
                        break
                elif trade['side'] == 'short':
                    if current_price >= trade['stop_loss'] or current_price <= trade['take_profit']:
                        trade['exit_price'] = current_price
                        trade['exit_time'] = current_time
                        balance += (trade['entry_price'] - trade['exit_price']) * trade['amount']
                        break

            # If the trade hasn't exited, exit it at the end of the data
            if trade['exit_price'] is None:
                trade['exit_price'] = last_price
                trade['exit_time'] = last_time
                if trade['side'] == 'long':
                    balance += (trade['exit_price'] - trade['entry_price']) * trade['amount']
                elif trade['side'] == 'short':
                    balance += (trade['entry_price'] - trade['exit_price']) * trade['amount']
    return balance