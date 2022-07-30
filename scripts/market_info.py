from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

class AccountInfo(ScriptStrategyBase):

    ticker = "BTC-USDT"
    exchange = "binance_perpetual_testnet"
    base,quote = ticker.split("-")
    markets = {"binance_perpetual_testnet":{"BTC-USDT"}}
    

    def on_tick(self):
        price = self.connectors[self.exchange].get_mid_price(self.ticker)

        msg = f"\n{self.ticker}: ${price}"
        self.logger().info(f"{msg}")
