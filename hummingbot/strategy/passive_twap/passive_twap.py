# BUILT-IN IMPORTS
import logging
from decimal import Decimal
from typing import (
    List,
    Optional
)



from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple

# MAIN STRATEGY CLASS
from hummingbot.strategy.strategy_py_base import StrategyPyBase
# LOGGER
from hummingbot.logger import HummingbotLogger

# INIT Logger variable
twap_logger = None


class PassiveTWAP(StrategyPyBase):

    # LOGGING
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global twap_logger
        if twap_logger is None:
            twap_logger = logging.getLogger(__name__)
        return twap_logger

    def __init__(
        self,
        market_infos: List[MarketTradingPairTuple],
        is_buy:bool,
        target_asset_amount:Decimal,
        TTC:float,
        GNT:float,
        MAX_SPREAD:Decimal,
        cancel_order_wait_time: Optional[float] = 60.0,
        status_report_interval:float=900.0
        ):
        """
        :param market_infos: list of market trading pairs
        :param is_buy: if the order is to buy
        :param target_asset_amount: qty of the order to place in (Quote For Buy Side) & (Base for Sell Side)
        :param TTC: Total Algo runTime in Minutes
        :param GNT: Total Number of Intervals During the Entire TTC
        :param MAX_SPREAD: Max Distance from Mid Price at the Start of Each Bin
        :param execution_state: execution state object with the conditions that should be satisfied to run each tick
        :param cancel_order_wait_time: how long to wait before cancelling an order >> Equal To
        :param status_report_interval: how often to report network connection related warnings, if any

        """
        
        # CHECK FOR TRADING PAIRS
        if len(market_infos)<1:
            raise ValueError("market_infos must not be empty")

        super().__init__()
        # Bundle up Trading Pairs info in one Dict
        self._market_infos = {
            (market_info.market, market_info.trading_pair): market_info
            for market_info in market_infos
        }

        # CHECKS and INIT Variables
        self._all_markets_ready = False
        self._place_orders = True
        self._first_order = True
        self.time_to_cancel = {}
        self._previous_time_stamp = 0   #??????????????????????
        self._last_timestamp = 0         #?????????????????????
        self._execution_state = True
        
        self._is_buy = is_buy
        ########## TIME COUNTERS
        # TOTAL DURATION >> USE AS REMAINING TIME FOR THE REST OF THE CODE
        self._remaining_time = TTC # Total Time/Duration
        # TOTAL BINS
        self._remaining_bins = GNT # Total Bins
        # TOTAL TIME PER BIN
        self._time_per_bin = TTC/GNT
        # REMAINING ALGO TIME
        self._bin_remaining_time = self._time_per_bin


        ########## AMOUNTS

        self._quantity_remaining = target_asset_amount
        self._MAX_SPREAD = MAX_SPREAD
        # Remaining Balance Per Bin
        self._balance_per_bin = self._quantity_remaining/(GNT-self._remaining_bins)
        # CURRENT SPREAD
        self._current_spread = MAX_SPREAD - (self._bin_remaining_time/2)
        # CANCEL ORDER RATE  = SPREAD REFRESH RATE
        #       DEFAULT REFRESH RATE => 10 SECONDS
        if cancel_order_wait_time<Decimal("10"):
            self._cancel_order_wait_time = Decimal('10')
        else:
            self._cancel_order_wait_time = cancel_order_wait_time
        # Reporting Interval for Any Errors
        self._status_report_interval = status_report_interval


        all_markets = set([market_info.market for market_info in market_infos])
        self.add_markets(list(all_markets))


        
        
    