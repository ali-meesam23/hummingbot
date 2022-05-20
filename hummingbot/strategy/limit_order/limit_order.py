#!/home/pi/miniforge3/envs/hummingbot/bin python

import logging
from decimal import Decimal

from hummingbot.core.event.events import OrderType
from hummingbot.logger import HummingbotLogger
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.strategy_py_base import StrategyPyBase

hws_logger = None

class LimitOrder(StrategyPyBase):

    # Creating logger
    def logger(cls) -> HummingbotLogger:
        global hws_logger
        if hws_logger is None:
            hws_logger = logging.getLogger(__name__)
        return hws_logger

    def __init__(self, market_info:MarketTradingPairTuple,) -> None:
        super().__init__()
        self._market_info = market_info
        self._connector_ready = False
        self._order_completed = False
        self.add_markets([market_info.market])
        self.quote_balance = self._market_info.quote_asset


    # Defining tick Method
    def tick(self,timestamp:float):
        if not self._connector_ready:
            self._connector_ready = self._market_info.market.ready
            if not self._connector_ready:
                self.logger().warning(f"{self._market_info.market.name} is not ready. Please wait ...")
                return
            else:
                self.logger().warning(f"{self._market_info.market.name} is ready. Trading Started")
            
        if not self._order_completed:
            # GET MID PRICE
            mid_price = self._market_info.get_mid_price()
            token = str(50/mid_price)
            # Executing the trade
            order_id = self.buy_with_specific_market(
                self._market_info,  # market trading pair tuple
                Decimal(token),   # amount
                OrderType.LIMIT,    # order_type
                mid_price           # Price
            )

            self.logger().info(f"Submitted limit buy order {order_id}")
            self._order_completed = True

    # Emits a log message when the order completes
    def did_complete_buy_order(self,order_completed_event):
        self.logger().info(f"You buy limit order {order_completed_event.order_id} has been executed")
        self.logger().info(order_completed_event)
        self.logger().warning(f"BALANCE: {self._market_info.base_balance} {self._market_info.base_asset}")
        self.logger().warning(f"BALANCE: {self._market_info.quote_balance} {self._market_info.base_asset}")