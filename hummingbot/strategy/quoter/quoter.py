#!/home/pi/miniforge3/envs/hummingbot/bin python

# BUILT-IN IMPORTS
import logging
import statistics
import time
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
import numpy as np

# CONNECTOR
from hummingbot.connector.exchange_base import ExchangeBase
# STRATEGY
from hummingbot.strategy.strategy_py_base import StrategyPyBase
from hummingbot.strategy.market_trading_pair_tuple import MarketTradingPairTuple
from hummingbot.strategy.conditional_execution_state import ConditionalExecutionState, RunAlwaysExecutionState
# CORE - DATA_TYPE
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.data_type.order_book import OrderBook
# CORE - CLOCK
from hummingbot.core.clock import Clock
# CORE - NETWORK
from hummingbot.core.network_iterator import NetworkStatus
# CORE - EVENTS
from hummingbot.core.event.events import (MarketOrderFailureEvent,
                                          OrderCancelledEvent,
                                          OrderExpiredEvent,
                                          OrderFilledEvent
                                          )
# PERFORMANCE METRICS
from hummingbot.client.performance import PerformanceMetrics
# LOGGER
from hummingbot.logger import HummingbotLogger


# INIT Logger variable
hws_logger = None

class Quoter(StrategyPyBase):
    def __init__(self,
        market_info: MarketTradingPairTuple,
        is_buy:bool,
        target_asset_amount:Decimal,
        TTC:float,
        GNT:float,
        MAX_SPREAD:Decimal,
        execution_state: ConditionalExecutionState = None,
        ) -> None:
        """
        :param market_info: market trading pairs object with ticker info
        :param is_buy: if the order is to buy
        :param target_asset_amount: qty of the order to place in (Quote For Buy Side) & (Base for Sell Side)
        :param TTC: Total Algo runTime in Minutes
        :param GNT: Total Number of Intervals During the Entire TTC
        :param MAX_SPREAD: Max Distance from Mid Price at the Start of Each Bin
        :param execution_state: execution state object with the conditions that should be satisfied to run each tick
        """
        super().__init__()
        self._market_info = market_info                                 ################# Inputs
        self._is_buy = is_buy                                           # ORDER
        self._target_asset_amount = Decimal(str(target_asset_amount))   # ORDER
        self._TTC = Decimal(str(TTC)) * Decimal('60')                   # COUNTER
        self._GNT = Decimal(str(GNT))                                   # COUNTER 
        self._MAX_SPREAD = Decimal(str(MAX_SPREAD))/Decimal("100")      # ORDER: Adjusting for %
        self._execution_state = execution_state or RunAlwaysExecutionState() # CONNECTION

        self._place_orders = True                                       # ORDER
        self._connector_ready = False                                   # CONNECTION
        self._all_markets_ready = False                                 # CONNECTION
        self.intervals = np.linspace(0,int(self._TTC),int(self._GNT)+1) # COUNTER: Bins are linked to the intervals | Splitting Total Duration Equally amoung bins
        
        self._current_balance = self._market_info.market.get_balance(self._market_info.base_asset)          # ASSET: Total Current Asset Balance
        # self._current_balance = market_info.base_balance
        self.logger().info(f"Current Balance (init): {self._current_balance}")
        self._start_time = Decimal(str(time.time()))                    # COUNTER
        
        self._last_timestamp = Decimal("0")                             # COUNTER: STARTING POINT
        self._remaining_time = self._TTC                                # COUNTER:  Total Time/Duration seconds
        self._remaining_bins = self._GNT                                      # COUNTER: Total Bins
        self._previous_bin = Decimal("0")                               # COUNTER: BINS
        self._current_bin = Decimal("0")                                # COUNTER: BINS
        self._time_per_bin = Decimal(self._TTC/self._GNT)               # COUNTER: BINS
        self._order_delay_time = self._time_per_bin                     # COUNTER: Once the Order is Executed in the bin
        self._counter = Decimal("0")                                    # COUNTER
        
        self._total_quantity_remaining = Decimal(abs(self._target_asset_amount-self._current_balance))
        
        self._MAX_SPREAD = -self._MAX_SPREAD if self._is_buy else self._MAX_SPREAD # Adjusting Spread +/- Bsed On Signal
        
        self._current_order_price = Decimal("0")
        self._current_order_size = Decimal("0")
        self.add_markets([market_info.market])                          # CONNECTION

    @classmethod
    def logger(cls) -> HummingbotLogger:
        """
        # CREATE A LOGGER
        """
        global hws_logger
        if hws_logger is None:
            hws_logger = logging.getLogger(__name__)
        return hws_logger

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
    
    ######################################################## STATUS #########################################################
    
    def configuration_status_lines(self,):
        lines = ["", "  Configuration:"]
        
        lines.append("    "
            f"Remaining amount: {PerformanceMetrics.smart_round(self._target_asset_amount - self._current_balance)} "
            f"{self._market_info.base_asset}    "
            f"Order price: {PerformanceMetrics.smart_round(self._current_order_price)} "
            f"{self._market_info.quote_asset}    "
            f"Order size: {PerformanceMetrics.smart_round(self._current_order_size)} "
            f"{self._market_info.base_asset}")

        lines.append(f"    Execution type: {self._execution_state}")

        return lines

    def filled_trades(self):
        """Returns a list of all filled trades generated from limit orders with the same 
        trade_type (buy/sell) the strategy has in its config
        !!!NOTE: self.trades is no where in the code other than this function!!!"""
        trade_type = TradeType.BUY if self._is_buy else TradeType.SELL
        return [
            trade for trade in self.trades
            if trade.trade_type == trade_type.name and trade.order_type == OrderType.LIMIT
        ]

    def format_status(self) -> str:
        market_info = self._market_info
        lines: list = []
        warning_lines: list = []

        lines.extend(self.configuration_status_lines())


        active_orders = self.market_info_to_active_orders.get(market_info, [])

        warning_lines.extend(self.network_warning([market_info]))

        markets_df = self.market_status_data_frame([market_info])
        lines.extend(["", "  Markets:"] + ["    " + line for line in markets_df.to_string().split("\n")])

        assets_df = self.wallet_balance_data_frame([market_info])
        lines.extend(["", "  Assets:"] + ["    " + line for line in assets_df.to_string().split("\n")])

        # See if there're any open orders.
        if len(active_orders) > 0:
            price_provider = None
            # for market_info in self._market_infos.values():
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

        lines.extend([f"  Pending amount: {PerformanceMetrics.smart_round(self._target_asset_amount - self._current_balance)} "
                        f"{market_info.base_asset}"])

        warning_lines.extend(self.balance_warning([market_info]))

        if warning_lines:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)

        return "\n".join(lines)

    #################################################################################################################

    def current_spread_ByTimeRemaining(self,c_time):
        """y=mx >> Linear
        c_time: Total Time Remaining
        """
        return Decimal((self._MAX_SPREAD/self._time_per_bin)*(c_time))
    
    #################################################################################################################

    ##################################################### EVENTS ############################################################

    def did_fill_order(self, order_filled_event:OrderFilledEvent):
        """
        Output log for filled order.
        :param order_filled_event: Order filled event
        """
        order_id: str = order_filled_event.order_id
        market_info = self.order_tracker.get_shadow_market_pair_from_order_id(order_id)

        if market_info is not None:
            self.log_with_clock(logging.INFO,
                                f"({market_info.trading_pair}) Limit {order_filled_event.trade_type.name.lower()} order of "
                                f"{order_filled_event.amount} {market_info.base_asset} filled.")
            if self._is_buy:
                self._current_balance += order_filled_event.amount
            else:
                self._current_balance -= order_filled_event.amount

    def did_complete_buy_order(self, order_completed_event):
        """
        Output log for completed buy order.
        :param order_completed_event: Order completed event
        """
        self.log_complete_order(order_completed_event)

    def did_complete_sell_order(self, order_completed_event):
        """
        Output log for completed sell order.
        :param order_completed_event: Order completed event
        """
        self.log_complete_order(order_completed_event)

    def log_complete_order(self, order_completed_event):
        """
        Output log for completed order.
        :param order_completed_event: Order completed event
        """
        order_id: str = order_completed_event.order_id
        market_info = self.order_tracker.get_market_pair_from_order_id(order_id)

        if market_info is not None:
            limit_order_record = self.order_tracker.get_limit_order(market_info, order_id)
            order_type = "buy" if limit_order_record.is_buy else "sell"
            self.log_with_clock(
                logging.INFO,
                f"({market_info.trading_pair}) Limit {order_type} order {order_id} "
                f"({limit_order_record.quantity} {limit_order_record.base_currency} @ "
                f"{limit_order_record.price} {limit_order_record.quote_currency}) has been filled."
            )

    def did_cancel_order(self, cancelled_event: OrderCancelledEvent):
        self.update_remaining_after_removing_order(cancelled_event.order_id, 'cancel')

    def did_fail_order(self, order_failed_event: MarketOrderFailureEvent):
        self.update_remaining_after_removing_order(order_failed_event.order_id, 'fail')

    def did_expire_order(self, expired_event: OrderExpiredEvent):
        self.update_remaining_after_removing_order(expired_event.order_id, 'expire')

    def update_remaining_after_removing_order(self, order_id: str, event_type: str):
        """
        Update quantity after cancelling the order 
        so a new order with the right amount can be placed for each bin
        IF ORDER CANCEL|FAIL|EXPIRE ADD ORDER AMOUNT BACK TO QUANTITY REMAINING
        """
        # GET MARKET INFO FROM ORDER ID
        market_info = self.order_tracker.get_market_pair_from_order_id(order_id)

        if market_info is not None:
            # GET ORDER INFO
            limit_order_record = self.order_tracker.get_limit_order(market_info, order_id)
            if limit_order_record is not None:
                self.log_with_clock(logging.INFO, f"Updating status after order {event_type} (id: {order_id})")
                
                self.logger().log(1,"*"*50+f"\n\n\nLimit Order Record: {limit_order_record}\n\n\n"+"*"*50)


    ####################################################### MARKET ##########################################################

    def process_market(self, market_info):
        """
        Checks if enough time has elapsed from previous order to place order and if so, calls place_orders_for_market().

        :param market_info: a market trading pair
        """
        refresh_rate = 30
        ######### REFRSH RATE 30 seconds
        # GET THE LATEST PRICE AND UPDATE WITH THE SPREAD
        # refresh rate >> 5 times per bin or every 5 seconds which ever is bigger
        if self._counter%Decimal(refresh_rate)==Decimal("0") or self._counter==Decimal("1") or int(self._remaining_bin_time)==10:
            ####################PRICE_UPDATE####################
            self.place_orders_for_market(market_info)
            
            
            
    def start(self, clock: Clock, timestamp: float):
        self._previous_timestamp = timestamp
        self._last_timestamp = timestamp

    def tick(self,timestamp:float):
        if self._current_balance==0:
            self._current_balance = self._market_info.market.get_balance(self._market_info.base_asset)
        """Updates every second"""
        ############### TOTAL QUANITYT REMAINING CHECK ###############
        if self._total_quantity_remaining<=0:
            self.logger().error(f"TOTAL REMAINING AMOUNT: {self._total_quantity_remaining}")
            return 
        
        ############### CHECK CONNECTION ###############
        if not self._connector_ready:
            self._connector_ready = self._market_info.market.ready
            if not self._connector_ready:
                self.logger().warning(f"{self._market_info.market.name} is not ready. Please wait ...")
                return
            else:
                self.logger().warning(f"{self._market_info.market.name} is ready. Trading Started")

        ############### BIN COUNTING ###############

        # CURRENT TIME ELAPSED
        c_time = Decimal(time.time())-self._start_time
        # IDENTIFY CURRENT BIN            
        for _i, i in enumerate(range(1,len(self.intervals))):
            # Interval Upper Bound
            x = Decimal(self.intervals[i-1])
            # Interval Lower Bound
            z = Decimal(self.intervals[i])
            # Get curent bin based on iternval
            if x<=c_time<z:
                self._current_bin = Decimal(_i+1)
                break # get z to calculate remaining time to calculate spread
            elif c_time>=self.intervals[-1]:
                self._current_bin = self._GNT
        
        # REMAINING BIN TIME
        self._remaining_bin_time = Decimal(z-c_time)
        # REMAINING BINS
        self._remaining_bins = self._GNT-self._current_bin

        ############### SPREAD CALCULATIONS ###############
        # CURRENT SPREAD >> CHANGE CTIME REMAINIGN WITH REFRESH RATE for last intervals
        if self._remaining_bin_time<Decimal('21'):
            ctime_for_spreadcalc = self._remaining_bin_time/Decimal("3")
        else:
            ctime_for_spreadcalc = self._remaining_bin_time
        # SPREAD CALC
        current_spread = self.current_spread_ByTimeRemaining(ctime_for_spreadcalc)
        ############### UPDATING ORDER PRICE ###############
        # GET MID PRICE
        current_price = self._market_info.get_mid_price()
        # GET ORDER PRICE -->> ADJUSTED FOR SPREAD
        self._current_order_price = current_price*(1+current_spread)

        # log_msg = f"{self._counter} Current Bin: {self._current_bin} >> remaining time {round(self._remaining_bin_time,1)} >> Spread: {round(current_spread*100,1)}%"
        # self.logger().info(log_msg)

        ############### SEPARATE COUNTER ###############
        self._counter+=Decimal('1')
        
        # QUANTITIES : TOTAL  || REMAINING QUANTITY PER BIN
        self._total_quantity_remaining = Decimal(abs(self._target_asset_amount-self._current_balance))


        try:
            self._execution_state.process_tick(timestamp,self)
        finally:
            self._last_timestamp = timestamp
        
    def process_tick(self, timestamp: float):
        """
        Clock tick entry point.
        For the TWAP strategy, this function simply checks for the readiness and connection status of markets, and
        then delegates the processing of each market info to process_market().
        """

        if not self._all_markets_ready:
            self._all_markets_ready = all([market.ready for market in self.active_markets])
            if not self._all_markets_ready:
                # Markets not ready yet. Don't do anything.
                return
        
        if not all([market.network_status is NetworkStatus.CONNECTED for market in self.active_markets]):
            self.logger().warning("WARNING: Some markets are not connected or are down at the moment. Market "
                                  "making may be dangerous when markets or networks are unstable.")
        
        # MODIFY GREATER THAN TO LESS THAN IF SHORTING?
        if self._current_bin<=self._GNT:
            self.process_market(self._market_info)
        else:
            self._execution_state._time_left = 0

    def cancel_active_orders(self):
        # Nothing to do here
        pass

    def place_orders_for_market(self, market_info):
        """
        Places an individual order specified by the user input if the user has enough balance and if the order quantity
        can be broken up to the number of desired orders
        :param market_info: a market trading pair
        """

        # ACTIVE ORDERS
        active_orders = self.market_info_to_active_orders.get(self._market_info, [])
        active_orders_t = self.active_limit_orders
        self.logger().info(f"\n\nACTIVE ORDERS:\n{active_orders_t}\n\n")
        
        # CANCEL ORDERS
        orders_to_cancel = (active_order
                            for active_order
                            in active_orders
                            )

        for order in orders_to_cancel:
            self.cancel_order(market_info, order.client_order_id)

        self.logger().info("Trying to place orders now. ")
        self._previous_timestamp = self.current_timestamp
        
        # self._market_info.market.get_balance(self._market_info.base_asset)
        # Expected Quantity on ith Bin - Current Quantity
        if self._is_buy:
            expected_balance = self._market_info.base_balance+((self._target_asset_amount-self._market_info.base_balance)/self._GNT*self._current_bin)
        else:
            expected_balance = self._market_info.base_balance-((-self._target_asset_amount+self._market_info.base_balance)/self._GNT*self._current_bin)
        

        self.logger().info(f"""
        Current Bin: {self._current_bin}
        StartingBalance: {self._market_info.base_balance}
        Expected Balance: {expected_balance}
        
        """)

        bin_remaining_quantity = Decimal(abs(Decimal(expected_balance)-Decimal(self._current_balance)))
        log_msg = f'Remaining Bin Quantity (PRE-ORDER): {bin_remaining_quantity}'
        self.logger().info(log_msg)
        
        # self.logger().info(f"Expected Balance: {expected_balance}")
        log_msg = f'TARGET / CURRENT: {self._target_asset_amount} / {self._current_balance} | BIN: {self._current_bin}'
        self.logger().info(log_msg)

        if bin_remaining_quantity != Decimal('0'):
    
            # EXCHANGE
            market: ExchangeBase = market_info.market
            # ORDER AMOUNT (FORMATTING)
            
            quantized_amount = market.quantize_order_amount(market_info.trading_pair, Decimal(bin_remaining_quantity))
            self._current_order_size = quantized_amount
            # ORDER PRICE
            quantized_price = market.quantize_order_price(market_info.trading_pair, Decimal(self._current_order_price))
            current_price = market_info.get_mid_price()

            log_msg=f"""
                {self._market_info.trading_pair}: CurrentPrice: ${current_price}
                Order Price: ${quantized_price} | SPRD: ${int(abs(self._current_order_price-current_price))}pts
                Quantity Remaining: {bin_remaining_quantity}"""
            self.logger().info(log_msg)

            self.logger().debug("Checking to see if the incremental order size is possible")
            self.logger().debug("Checking to see if the user has enough balance to place orders")

            if quantized_amount != 0:
                if self.has_enough_balance(market_info, quantized_amount):
                    if self._is_buy:
                        self.buy_with_specific_market(market_info,
                                                                amount=quantized_amount,
                                                                order_type=OrderType.LIMIT,
                                                                price=quantized_price)
                        self.logger().info("Limit buy order has been placed")
                    else:
                        self.sell_with_specific_market(market_info,
                                                                amount=quantized_amount,
                                                                order_type=OrderType.LIMIT,
                                                                price=quantized_price
                                                                )
                        self.logger().info("Limit sell order has been placed")
                else:
                    self.logger().info("Not enough balance to run the strategy. Please check balances and try again.")
            else:
                self.logger().warning("Not possible to break the order into the desired number of segments.")
        else:
            self.logger().info(f"Inside PlaceMarketOrder >>> Fully Executed Bin: {bin_remaining_quantity} Coins Left")

    def has_enough_balance(self, market_info, amount: Decimal):
        """
        Checks to make sure the user has the sufficient balance in order to place the specified order

        :param market_info: a market trading pair
        :param amount: order amount
        :return: True if user has enough balance, False if not
        """
        market: ExchangeBase = market_info.market
        base_asset_balance = market.get_balance(market_info.base_asset)
        quote_asset_balance = market.get_balance(market_info.quote_asset)
        order_book: OrderBook = market_info.order_book
        price = order_book.get_price_for_volume(True, float(amount)).result_price

        return quote_asset_balance >= (amount * Decimal(price)) \
            if self._is_buy \
            else base_asset_balance >= amount
''