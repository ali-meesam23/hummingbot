from hummingbot.client.config.config_var import ConfigVar


# Prompt: Connector Value Set By User
def market_prompt()-> str:
    connector = limit_order_config_map.get("connector").value
    return f"Enter the token trading pair on {connector} >>>"

# List of Parameters Defined By the Strategy
limit_order_config_map = {
    "strategy": 
    ConfigVar(
        key="strategy",
        prompt="",
        default="limit_order"
    ),
    "connector":
    ConfigVar(
        key="connector",
        prompt="Enter the name of the exhange >>> ",
        prompt_on_new=True
    ),
    "market":
    ConfigVar(
        key="market",
        prompt=market_prompt,
        prompt_on_new=True
    )
}