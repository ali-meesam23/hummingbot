from datetime import datetime
from typing import (
    List,
    Tuple,
)

# MARKET DATA (BUILT-IN)
from sys import exc_info
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

# STRATEGY
from hummingbot.strategy.passive_twap import (
    PassiveTWAP
)
# CONFIGURATION
from hummingbot.strategy.passive_twap.passive_twap_config_map import passive_twap_config_map


def start(self):
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    try:
        
        # EXCHANGE
        exchange = passive_twap_config_map.get("connector").value.lower()
        # PAIR
        raw_market_trading_pair = passive_twap_config_map.get("trading_pair").value
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
        # ASSETS (TUPLE) >> FROM EXCHANGE AND TRADING PAIR
        try:
            assets: Tuple[str, str] = self._initialize_market_assets(exchange, [raw_market_trading_pair])[0]
        except ValueError as e:
            self._notify(str(e))
            return

        is_buy = trade_side == "buy"
        # Priming inputs for Market Data
        market_names: List[Tuple[str, List[str]]] = [(exchange, [raw_market_trading_pair])]
        self._initialize_markets(market_names)
        maker_data = [self.markets[exchange], raw_market_trading_pair] + list(assets)
        self.market_trading_pair_tuples = [MarketTradingPairTuple(*maker_data)]

        self.strategy = PassiveTWAP(market_infos=[MarketTradingPairTuple(*maker_data)],
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
