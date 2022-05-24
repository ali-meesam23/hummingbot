# MARKET DATA (BUILT-IN)
from sys import exc_info
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

# STRATEGY
from hummingbot.strategy.twap_v0 import (
    TWAP_V0
)
# CONFIGURATION
from hummingbot.strategy.passive_twap.passive_twap_config_map import passive_twap_config_map


def start(self):
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    try:
        
        # EXCHANGE
        exchange = passive_twap_config_map.get("connector").value.lower()
        # PAIR
        market = passive_twap_config_map.get("trading_pair").value
        # SIDE
        trade_side = passive_twap_config_map.get("trade_side").value
        # AMOUNT
        target_asset_amount = passive_twap_config_map.get("target_asset_amount").value
        # DURATION
        TTC = passive_twap_config_map.get("TTC").value
        # BIN SIZES
        GNT = passive_twap_config_map.get("GNT").value
        # MAX SPREAD
        MAX_SPREAD = passive_twap_config_map.get("MAX_SPREAD").value
        
        is_buy = trade_side == "buy"
        # INITIALIZING MARKET_INFO OBJECT
        self._initialize_markets([(exchange,[market])])
        base,quote = market.split('-')
        market_info = MarketTradingPairTuple(self.markets[exchange],market,base,quote)
        self.market_trading_pair_tuples = [market_info]
        # INITIALIZING THE STRATEGY
        self.strategy = TWAP(market_info=market_info,
            is_buy=is_buy,
            target_asset_amount=target_asset_amount,
            TTC=TTC,
            GNT = GNT,
            MAX_SPREAD=MAX_SPREAD
        )
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    except Exception as e:
        self._notify(str(e))
        self.logger().error("Unknown error during initialization.", exc_info=True)
