#!/home/pi/miniforge3/envs/hummingbot/bin python

# BUILT-IN IMPORTS
import logging
import statistics
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
# CONNECTOR
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.core.clock import Clock
# MARKET DATA
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
# CORE - DATA_TYPE
from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.data_type.common import OrderType, TradeType
# QUOTER OOP
from hummingbot.strategy.quoter.quoter_events import QuoterEvents
from hummingbot.strategy.quoter.quoter_market import QuoterMarket
from hummingbot.strategy.quoter.quoter_status import QuoterStatus

# MAIN STRATEGY CLASS
from hummingbot.strategy.strategy_py_base import StrategyPyBase
# LOGGER
from hummingbot.logger import HummingbotLogger


# INIT Logger variable
hws_logger = None

class Quoter(StrategyPyBase,QuoterEvents,QuoterMarket,QuoterStatus):
    
    # CREATE A LOGGER
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global hws_logger
        if hws_logger is None:
            hws_logger = logging.getLogger(__name__)
        return hws_logger
    
    def __init__(self,
        market_info: MarketTradingPairTuple,
        is_buy:bool,
        target_asset_amount:Decimal,
        TTC:float,
        GNT:float,
        MAX_SPREAD:Decimal,
        cancel_order_wait_time: Optional[float] = 60.0,
        status_report_interval:float=900.0,
        ) -> None:
        """
        :param market_info: market trading pairs object with ticker info
        :param is_buy: if the order is to buy
        :param target_asset_amount: qty of the order to place in (Quote For Buy Side) & (Base for Sell Side)
        :param TTC: Total Algo runTime in Minutes
        :param GNT: Total Number of Intervals During the Entire TTC
        :param MAX_SPREAD: Max Distance from Mid Price at the Start of Each Bin
        :param execution_state: execution state object with the conditions that should be satisfied to run each tick
        :param cancel_order_wait_time: how long to wait before cancelling an order >> Equal To
        :param status_report_interval: how often to report network connection related warnings, if any

        """
        super().__init__()

        self._market_info = market_info
        self._is_buy = is_buy
        self._target_asset_amount = target_asset_amount
        self._TTC = TTC * 60
        self._GNT = GNT
        self._MAX_SPREAD = MAX_SPREAD


        self.add_markets([market_info.market])
        self.quote_balance =self._market_info.quote_asset
        self.base_balance = self._market_info.base_asset

        self._connector_ready = False
        self._all_markets_ready = False

        self._first_order = True
        self._place_orders = True
        self._order_completed = False
        self._execution_state = True

        # CHECKS and INIT Variables
        self.time_to_cancel = {}
        self._previous_time_stamp = 0   # TRACKING
        self._last_timestamp = 0         # STARTING POINT
        
        ########## COUNTERS
        # TOTAL DURATION >> USE AS REMAINING TIME FOR THE REST OF THE CODE
        self._remaining_time = self._TTC # Total Time/Duration seconds
        # TOTAL BINS
        self._remaining_bins = GNT # Total Bins
        self._current_bin = 0
        # TOTAL TIME PER BIN
        self._time_per_bin = TTC/GNT
        self._order_delay_time = self._time_per_bin # Once the Order is Executed in the bin
        # REMAINING ALGO TIME
        self._bin_remaining_time = self._time_per_bin

        ########## AMOUNTS
        self._quantity_remaining = target_asset_amount

        # Remaining Balance Per Bin
        self._order_size = self._quantity_remaining/(GNT-self._remaining_bins)
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

    @property
    def active_bids(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_bids

    @property
    def active_asks(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_asks

    @property
    def active_limit_orders(self) -> List[Tuple[ExchangeBase, LimitOrder]]:
        return self.order_tracker.active_limit_orders

    @property
    def in_flight_cancels(self) -> Dict[str, float]:
        return self.order_tracker.in_flight_cancels

    @property
    def market_info_to_active_orders(self) -> Dict[MarketTradingPairTuple, List[LimitOrder]]:
        return self.order_tracker.market_pair_to_active_orders

    @property
    def place_orders(self):
        return self._place_orders
    
    @property
    def get_order_prices(self):
        """
        Get Order prices for each trading pair on the exchange
        return >> {exch:{pair:value,...},...}
        """
        curr_spread = -1*self._current_spread if self._is_buy else self._current_spread
        prices = {}
        
        pair = self._market_info.trading_pair
        if pair not in prices:
            prices[pair] = Decimal(self._market_info.get_mid_price()+curr_spread)
        return prices
    

    def tick(self):
        """Updates every second"""
        # CHECK CONNECTION
        if not self._connector_ready:
            self._connector_ready = self._market_info.market.ready
            if not self._connector_ready:
                self.logger().warning(f"{self._market_info.market.name} is not ready. Please wait ...")
                return
            else:
                self.logger().warning(f"{self._market_info.market.name} is ready. Trading Started")

        self.logger().warning(f"Current Bin: {self._current_bin}")


    def start(self, clock: Clock, timestamp: float):
        self.logger().info(f"Waiting for {self._order_delay_time} to place orders")
        self._previous_timestamp = timestamp
        self._last_timestamp = timestamp



        
    
