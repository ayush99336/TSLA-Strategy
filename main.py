from AlgorithmImports import *
import numpy as np

class TrendFollowingStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 1, 1)  # Set Start Date
        self.SetEndDate(2023, 1, 1)    # Set End Date
        self.SetCash(100000)           # Set Strategy Cash

        self.initial_cash = self.Portfolio.Cash  # Store the initial cash amount
        self.symbol = self.AddEquity("TSLA", Resolution.Daily).Symbol

        # Define the moving average periods
        self.fast_period = 50
        self.slow_period = 200

        # Create the moving average indicators
        self.fast_ma = self.SMA(self.symbol, self.fast_period, Resolution.Daily)
        self.slow_ma = self.SMA(self.symbol, self.slow_period, Resolution.Daily)

        # Set the benchmark
        self.SetBenchmark(self.symbol)

        # Set warmup period to allow indicators to be ready
        self.SetWarmUp(self.slow_period)

        # Risk management parameters
        self.stop_loss_pct = 0.05  # 5% stop loss
        self.take_profit_pct = 0.1  # 10% take profit

        self.entry_price = None

        # Tracking daily portfolio values to calculate returns
        self.daily_portfolio_values = []

    def OnData(self, data):
        if self.IsWarmingUp:
            return

        if not self.slow_ma.IsReady or not self.fast_ma.IsReady:
            return

        if not data.ContainsKey(self.symbol):
            return

        if data[self.symbol] is None or not hasattr(data[self.symbol], 'Close'):
            self.Debug(f"No valid data for {self.symbol} at {self.Time}")
            return

        holdings = self.Portfolio[self.symbol].Quantity
        price = data[self.symbol].Close

        # Risk management: Check for stop loss or take profit
        if holdings > 0 and self.entry_price:
            if price < self.entry_price * (1 - self.stop_loss_pct):
                self.Liquidate(self.symbol)
                self.Log(f"Stop loss hit, selling {self.symbol} at {price}")
                return
            elif price > self.entry_price * (1 + self.take_profit_pct):
                self.Liquidate(self.symbol)
                self.Log(f"Take profit hit, selling {self.symbol} at {price}")
                return

        # Check for a bullish crossover (Golden Cross)
        if self.fast_ma.Current.Value > self.slow_ma.Current.Value and holdings <= 0:
            self.SetHoldings(self.symbol, 1)
            self.entry_price = price
            self.Log(f"Buying {self.symbol} at {price}")

        # Check for a bearish crossover (Death Cross)
        elif self.fast_ma.Current.Value < self.slow_ma.Current.Value and holdings > 0:
            self.Liquidate(self.symbol)
            self.Log(f"Selling {self.symbol} at {price}")

    def OnEndOfDay(self, symbol):
        if symbol != self.symbol:
            return

        # Log daily performance metrics
        self.daily_portfolio_values.append(self.Portfolio.TotalPortfolioValue)
        self.Log(f"Date: {self.Time}")
        self.Log(f"Portfolio Value: {self.Portfolio.TotalPortfolioValue}")

        if self.Securities.ContainsKey(self.symbol) and self.Securities[self.symbol].Close != 0:
            self.Log(f"TSLA Price: {self.Securities[self.symbol].Close}")
        else:
            self.Log("TSLA Price: Not available")

        self.Log(f"Fast MA: {self.fast_ma.Current.Value}")
        self.Log(f"Slow MA: {self.slow_ma.Current.Value}")
        self.Log(f"Holdings: {self.Portfolio[self.symbol].Quantity}")
        self.Log("--------------------")
        
    def OnEndOfAlgorithm(self):
        # Calculate Sharpe Ratio manually
        returns = np.diff(self.daily_portfolio_values) / self.daily_portfolio_values[:-1]
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        risk_free_rate = 0.01 / 252  # Annual risk-free rate divided by trading days
        sharpe_ratio = (avg_return - risk_free_rate) / std_return if std_return != 0 else 0

        # Calculate Total Return
        final_value = self.Portfolio.TotalPortfolioValue
        total_return = (final_value - self.initial_cash) / self.initial_cash

        self.Log(f"Sharpe Ratio: {sharpe_ratio}")
        self.Log(f"Total Return: {total_return * 100:.2f}%")
