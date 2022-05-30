from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

class AccountInfo(ScriptStrategyBase):

    ticker = "BTC-USDT"
    exchange = "kucoin_testnet"
    base,quote = ticker.split("-")
    markets = {"kucoin_testnet":{"BTC-USDT"}}

    def on_tick(self):
        base_balance = self.connectors[self.exchange].get_balance(self.base)
        quote_balance = self.connectors[self.exchange].get_balance(self.quote)
        msg = f"Balances: {base_balance}Tkns | ${quote_balance}"
        self.logger().info(f"{msg}")
