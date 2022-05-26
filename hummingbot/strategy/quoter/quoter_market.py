# from decimal import Decimal
# from hummingbot.connector.exchange_base import ExchangeBase
# from hummingbot.core.data_type.order_book import OrderBook
# from hummingbot.core.data_type.common import OrderType

# class QuoterMarket:
#     def has_enough_balance(self, market_info, amount: Decimal):
#         """
#         Checks to make sure the user has the sufficient balance in order to place the specified order

#         :param market_info: a market trading pair
#         :param amount: order amount
#         :return: True if user has enough balance, False if not
#         """
#         market: ExchangeBase = market_info.market
#         base_asset_balance = market.get_balance(market_info.base_asset)
#         quote_asset_balance = market.get_balance(market_info.quote_asset)
#         order_book: OrderBook = market_info.order_book
#         price = order_book.get_price_for_volume(True, float(amount)).result_price

#         return quote_asset_balance >= (amount * Decimal(price)) \
#             if self._is_buy \
#             else base_asset_balance >= amount

#     def place_orders_for_market(self, market_info,order_price):
#         """
#         Places an individual order specified by the user input if the user has enough balance and if the order quantity
#         can be broken up to the number of desired orders
#         :param market_info: a market trading pair
#         """
#         # EXCHANGE
#         market: ExchangeBase = market_info.market
#         # ORDER AMOUNT
#         curr_order_amount = self._quantity_remaining
#         # ORDER AMOUNT FORMATTING
#         quantized_amount = market.quantize_order_amount(market_info.trading_pair, Decimal(curr_order_amount))
#         # ORDER PRICE
#         quantized_price = market.quantize_order_price(market_info.trading_pair, Decimal(self._current_order_price))

#         self.logger().debug("Checking to see if the incremental order size is possible")
#         self.logger().debug("Checking to see if the user has enough balance to place orders")

#         if quantized_amount != 0:
#             if self.has_enough_balance(market_info, quantized_amount):
#                 if self._is_buy:
#                     order_id = self.buy_with_specific_market(market_info,
#                                                              amount=quantized_amount,
#                                                              order_type=OrderType.LIMIT,
#                                                              price=quantized_price)
#                     self.logger().info("Limit buy order has been placed")
#                 else:
#                     order_id = self.sell_with_specific_market(market_info,
#                                                               amount=quantized_amount,
#                                                               order_type=OrderType.LIMIT,
#                                                               price=quantized_price)
#                     self.logger().info("Limit sell order has been placed")
#                 # self._time_to_cancel[order_id] = self.current_timestamp + self._cancel_order_wait_time

#                 self._quantity_remaining = Decimal(self._quantity_remaining) - quantized_amount

#             else:
#                 self.logger().info("Not enough balance to run the strategy. Please check balances and try again.")
#         else:
#             self.logger().warning("Not possible to break the order into the desired number of segments.")