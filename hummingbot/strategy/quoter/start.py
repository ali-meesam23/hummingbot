from hummingbot.strategy.quoter.quoter import Quoter
from hummingbot.strategy.quoter.quoter_config_map import  quoter_config_map as c_map
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

<<<<<<< HEAD:hummingbot/strategy/twap_v0/start.py
# STRATEGY
from hummingbot.strategy.twap_v0 import (
    TWAP_V0
)
# CONFIGURATION
from hummingbot.strategy.passive_twap.passive_twap_config_map import passive_twap_config_map

=======
>>>>>>> feat/script_strategy:hummingbot/strategy/quoter/start.py

def start(self):
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    try:
        
        # EXCHANGE
        exchange = c_map.get("connector").value.lower()
        # PAIR
        market = c_map.get("trading_pair").value
        # SIDE
        trade_side = c_map.get("trade_side").value
        # AMOUNT
        target_asset_amount = c_map.get("target_asset_amount").value
        # DURATION
        TTC = c_map.get("TTC").value
        # BIN SIZES
        GNT = c_map.get("GNT").value
        # MAX SPREAD
        MAX_SPREAD = c_map.get("MAX_SPREAD").value
        
        is_buy = trade_side == "buy"
        # INITIALIZING MARKET_INFO OBJECT
        self._initialize_markets([(exchange,[market])])
        base,quote = market.split('-')
        market_info = MarketTradingPairTuple(self.markets[exchange],market,base,quote)
        self.market_trading_pair_tuples = [market_info]
        # INITIALIZING THE STRATEGY
        self.strategy = Quoter(market_info=market_info,
            is_buy=is_buy,
            target_asset_amount=target_asset_amount,
            TTC=TTC,
            GNT = GNT,
            MAX_SPREAD=MAX_SPREAD
        )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    except Exception as e:
        self.notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)
