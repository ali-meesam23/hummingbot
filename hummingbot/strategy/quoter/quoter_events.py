import logging
from hummingbot.core.event.events import (MarketOrderFailureEvent,
                                          OrderCancelledEvent,
                                          OrderExpiredEvent,
                                          )
from hummingbot.core.data_type.common import OrderType, TradeType


class QuoterEvents:
    def did_fill_order(self, order_filled_event):
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
        market_info = self.order_tracker.get_market_pair_from_order_id(order_id)

        if market_info is not None:
            limit_order_record = self.order_tracker.get_limit_order(market_info, order_id)
            if limit_order_record is not None:
                self.log_with_clock(logging.INFO, f"Updating status after order {event_type} (id: {order_id})")
                self._quantity_remaining += limit_order_record.quantity


    def filled_trades(self):
        """Returns a list of all filled trades generated from limit orders with the same 
        trade_type (buy/sell) the strategy has in its config
        !!!NOTE: self.trades is no where in the code other than this function!!!"""
        trade_type = TradeType.BUY if self._is_buy else TradeType.SELL
        return [
            trade for trade in self.trades
            if trade.trade_type == trade_type.name and trade.order_type == OrderType.LIMIT
        ]