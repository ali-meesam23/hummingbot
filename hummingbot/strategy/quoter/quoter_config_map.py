from decimal import Decimal
from hummingbot.client.config.config_var import ConfigVar
# VALIDATORS
from hummingbot.client.config.config_validators import (
    validate_exchange,
    validate_decimal
)
# SETTINGS
from hummingbot.client.settings import (
    required_exchanges
)

############ HELPER FUNCTIONS ############
def str2bool(value: str):
    return str(value).lower() in ("yes", "y", "true", "t", "1")

############ PROMPTS ############
def market_prompt():
    connector = quoter_config_map.get('connector').value
    return f"{connector} >> Trading Pair: "

def target_asset_amount_prompt():
    """'token amount'"""
    trading_pair = quoter_config_map.get("trading_pair").value
    base_token, _ = trading_pair.split("-")
    return f"What is the total amount of {base_token} to be traded? (Default is 1.0) >>> "


############ VALIDATIONS ############
def validate_algo_duration(value:str=None):
    """Invalidates non-decimal input and check if duration is greater than 0"""
    result = validate_decimal(value,min_value=Decimal("1"),inclusive=False)
    if result:
        return result

def validate_spread(value:str=None):
    """Invalidates non-decimal input and check if duration is greater than 0"""
    result = validate_decimal(value,min_value=Decimal("0"),inclusive=False)
    if result:
        return result



quoter_config_map = {
    "strategy":
        ConfigVar(key="strategy",
                  prompt=None,
                  default="quoter"),
    "connector":ConfigVar(
            key="connector",
            prompt="Exchange: ",
            # validator=validate_exchange,
            # on_validated=lambda value: required_exchanges.append(value),
            prompt_on_new=True    
        ),
    "trading_pair":ConfigVar(
        key='trading_pair',
        prompt=market_prompt,
        prompt_on_new=True
    ),
    "trade_side":ConfigVar(
        key='trade_side',
        prompt="What operation will be executed? (buy/sell) >>> ",
        type_str="str",
        validator=lambda v: None if v in {"buy", "sell", ""} else "Invalid operation type.",
        default="buy",
        prompt_on_new=True
    ),
    "target_asset_amount":ConfigVar(
        key="target_asset_amount",
        prompt=target_asset_amount_prompt,
        default=1.0,
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=Decimal("0"), inclusive=False),
        prompt_on_new=True),
    "TTC":ConfigVar(
        key="TTC",
        prompt="What is the duration of the execution (minutes)? "
                ">>> ",
        default=60.0,
        type_str="decimal",
        validator=validate_algo_duration,
        prompt_on_new=True),

    "GNT":ConfigVar(
        key="GNT",
        prompt="Number of Time Intervals for the entire run? "
                ">>> ",
        default=60.0,
        type_str="decimal",
        validator=validate_algo_duration,
        prompt_on_new=True),
    "MAX_SPREAD":ConfigVar(
        key="MAX_SPREAD",
        prompt="Maximum Spread To Place First Order in Each Interval? "
                ">>> ",
        default=30.0,
        type_str="decimal",
        validator=validate_spread,
        prompt_on_new=True)
}