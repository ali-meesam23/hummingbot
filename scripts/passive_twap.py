from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.connector.exchange_base import ExchangeBase

class PassiveTWAP(ScriptStrategyBase):
    pass

    @property
    def connector(self) -> ExchangeBase:
        """
        The only connector in this strategy, define it here for easy access
        """
        return self.connectors[self.connector_name]


