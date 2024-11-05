# trading_app/management/commands/run_backtest.py

from django.core.management.base import BaseCommand
from trading_app.trading_bot import (
    fetch_ohlcv_data,
    generate_signals,
    backtest_trade,
    simulate_trade_execution,
    INITIAL_BALANCE,
    SYMBOLS,
    TIMEFRAME,
    BASE_ORDER_AMOUNTS,  # Make sure you're importing the dictionary
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT
)

class Command(BaseCommand):
    help = 'Runs the backtesting strategy'

    def handle(self, *args, **options):
        for SYMBOL in SYMBOLS:
            trades = []  # Initialize trades list for each symbol
            df = fetch_ohlcv_data(SYMBOL, TIMEFRAME)
            if df is not None:
                df = generate_signals(df)
                balance = INITIAL_BALANCE

                for i in range(1, len(df)):
                    signal = df['signal'].iloc[i]
                    current_price = df['close'].iloc[i]
                    entry_time = df['timestamp'].iloc[i]  # Get entry time
                    if signal != 0:
                        amount = BASE_ORDER_AMOUNTS[SYMBOL]  # Get the amount for the current symbol
                        backtest_trade(SYMBOL, signal, amount, current_price, entry_time, trades)

                final_balance = simulate_trade_execution(balance, trades, df)

                # --- Calculate Performance Metrics ---
                total_trades = len(trades)
                winning_trades = 0
                total_profit = 0
                max_drawdown = 0
                peak_balance = INITIAL_BALANCE

                for trade in trades:
                    if trade['exit_price'] is not None:
                        profit = (trade['exit_price'] - trade['entry_price']) * trade['amount'] if trade['side'] == 'long' else \
                                 (trade['entry_price'] - trade['exit_price']) * trade['amount']
                        total_profit += profit
                        if profit > 0:
                            winning_trades += 1
                        peak_balance = max(peak_balance, balance)
                        drawdown = (peak_balance - balance) / peak_balance
                        max_drawdown = max(max_drawdown, drawdown)

                win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

                self.stdout.write(self.style.SUCCESS(f'Symbol: {SYMBOL}'))
                self.stdout.write(self.style.SUCCESS(f'Initial Balance: {INITIAL_BALANCE}'))
                self.stdout.write(self.style.SUCCESS(f'Final Balance: {final_balance}'))
                self.stdout.write(self.style.SUCCESS(f'Total Trades: {total_trades}'))
                self.stdout.write(self.style.SUCCESS(f'Winning Trades: {winning_trades}'))
                self.stdout.write(self.style.SUCCESS(f'Win Rate: {win_rate:.2f}%'))
                self.stdout.write(self.style.SUCCESS(f'Total Profit: {total_profit:.2f}'))
                self.stdout.write(self.style.SUCCESS(f'Maximum Drawdown: {max_drawdown * 100:.2f}%'))
                self.stdout.write(self.style.SUCCESS(f'Final Balance for {SYMBOL}: {final_balance} with base order amount {BASE_ORDER_AMOUNTS[SYMBOL]}'))
