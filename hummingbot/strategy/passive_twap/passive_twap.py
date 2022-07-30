# BUILT-IN IMPORTS
import logging
import statistics
from decimal import Decimal
from typing import (
    List,
    Dict,
    Optional,
    # Tuple
)


# MARKET DATA
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
# CONNECTOR
from hummingbot.connector.exchange_base import ExchangeBase

# CORE - DATA_TYPE
from hummingbot.core.data_type.limit_order import LimitOrder
# from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.common import OrderType, TradeType

# MAIN STRATEGY CLASS
from hummingbot.strategy.strategy_py_base import StrategyPyBase

# LOGGER
from hummingbot.logger import HummingbotLogger
# PERFORMANCE METRICS
from hummingbot.client.performance import PerformanceMetrics

# INIT Logger variable
hws_logger = None

class PassiveTWAP(StrategyPyBase):

    @classmethod
    def logger(cls)->HummingbotLogger:
        global hws_logger
        if hws_logger is None:
            hws_logger = logging.getLogger(__name__)
        return hws_logger

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
        )->None:
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


        all_markets = set([market_info.market for market_info in market_infos])
        self.add_markets(list(all_markets))


    @property
    def market_info_to_active_orders(self) -> Dict[MarketTradingPairTuple, List[LimitOrder]]:
        return self.order_tracker.active_limit_orders

    @property
    def get_order_prices(self):
        """
        Get Order prices for each trading pair on the exchange
        return >> {exch:{pair:value,...},...}
        """
        curr_spread = -1*self._current_spread if self._is_buy else self._current_spread
        prices = {}
        for market_info in self._market_infos.values():
            pair = market_info.trading_pair
            if pair not in prices:
                prices[pair] = Decimal(market_info.get_mid_price()+curr_spread)
        return prices


    def filled_trades(self):
        """Returns a list of all filled trades generated from limit orders with the same 
        trade_type (buy/sell) the strategy has in its config
        !!!NOTE: self.trades is no where in the code other than this function!!!"""
        trade_type = TradeType.BUY if self._is_buy else TradeType.SELL
        return [
            trade for trade in self.trades
            if trade.trade_type == trade_type.name and trade.order_type == OrderType.LIMIT
        ]
    
    # ======================= STATUS =======================
    def configuration_status_lines(self,):
        lines = ["", "  Configuration:"]

        for market_info in self._market_infos.values():

            lines.append("    "
                         f"Remaining amount: {PerformanceMetrics.smart_round(self._quantity_remaining)} "
                         f"{market_info.quote}    "
                         f"Order price: {PerformanceMetrics.smart_round(self.get_order_prices[market_info.trading_pair])} "
                         f"{market_info.quote_asset}    "
                         f"Order size: {PerformanceMetrics.smart_round(self._order_size)} "
                         f"{market_info.base_asset}")

        lines.append(f"    Execution type: {self._execution_state}")

        return lines

    def format_status(self) -> str:
        lines: list = []
        warning_lines: list = []

        lines.extend(self.configuration_status_lines())

        for market_info in self._market_infos.values():

            active_orders = self.market_info_to_active_orders.get(market_info, [])

            warning_lines.extend(self.network_warning([market_info]))

            markets_df = self.market_status_data_frame([market_info])
            lines.extend(["", "  Markets:"] + ["    " + line for line in markets_df.to_string().split("\n")])

            assets_df = self.wallet_balance_data_frame([market_info])
            lines.extend(["", "  Assets:"] + ["    " + line for line in assets_df.to_string().split("\n")])

            # See if there're any open orders.
            if len(active_orders) > 0:
                price_provider = None
                for market_info in self._market_infos.values():
                    price_provider = market_info
                if price_provider is not None:
                    df = LimitOrder.to_pandas(active_orders, mid_price=price_provider.get_mid_price())
                    if self._is_buy:
                        # Descend from the price closest to the mid price
                        df = df.sort_values(by=['Price'], ascending=False)
                    else:
                        # Ascend from the price closest to the mid price
                        df = df.sort_values(by=['Price'], ascending=True)
                    df = df.reset_index(drop=True)
                    df_lines = df.to_string().split("\n")
                    lines.extend(["", "  Active orders:"] +
                                 ["    " + line for line in df_lines])
            else:
                lines.extend(["", "  No active maker orders."])

            filled_trades = self.filled_trades()
            average_price = (statistics.mean([trade.price for trade in filled_trades])
                             if filled_trades
                             else Decimal(0))
            lines.extend(["",
                          f"  Average filled orders price: "
                          f"{PerformanceMetrics.smart_round(average_price)} "
                          f"{market_info.quote_asset}"])

            lines.extend([f"  Pending amount: {PerformanceMetrics.smart_round(self._quantity_remaining)} "
                          f"{market_info.base_asset}"])

            warning_lines.extend(self.balance_warning([market_info]))

        if warning_lines:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)

        return "\n".join(lines)

    # =======================================================
    