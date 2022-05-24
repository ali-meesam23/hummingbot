# PERFORMANCE METRICS
from decimal import Decimal
import statistics
from hummingbot.client.performance import PerformanceMetrics
from hummingbot.core.data_type.limit_order import LimitOrder

class QuoterStatus:
    # ======================= STATUS =======================
    def configuration_status_lines(self,):
        lines = ["", "  Configuration:"]

        lines.append("    "
            f"Remaining amount: {PerformanceMetrics.smart_round(self._quantity_remaining)} "
            f"{self._market_info.base}    "
            f"Order price: {PerformanceMetrics.smart_round(self.get_order_prices[self._market_info.trading_pair])} "
            f"{self._market_info.quote_asset}    "
            f"Order size: {PerformanceMetrics.smart_round(self._order_size)} "
            f"{self._market_info.base_asset}")

        lines.append(f"    Execution type: {self._execution_state}")

        return lines

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

        lines.extend([f"  Pending amount: {PerformanceMetrics.smart_round(self._quantity_remaining)} "
                        f"{market_info.base_asset}"])

        warning_lines.extend(self.balance_warning([market_info]))

        if warning_lines:
            lines.extend(["", "*** WARNINGS ***"] + warning_lines)

        return "\n".join(lines)
    # =======================================================
