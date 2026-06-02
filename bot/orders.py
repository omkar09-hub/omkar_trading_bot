from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.validators import validate_all
from bot.logging_config import logger

def place_order(client: BinanceFuturesClient, symbol: str, side: str, order_type: str, quantity, price=None, stop_price=None, time_in_force="GTC") -> dict:
    """
    Validates and places an order on Binance Futures.
    
    Parameters:
    - client: Instance of BinanceFuturesClient.
    - symbol: Trading symbol (e.g., 'BTCUSDT').
    - side: Order side ('BUY' or 'SELL').
    - order_type: Order type ('MARKET', 'LIMIT', 'STOP_MARKET').
    - quantity: Quantity to trade.
    - price: Limit price (required for LIMIT orders).
    - stop_price: Stop/Trigger price (required for STOP_MARKET orders).
    - time_in_force: Time in force policy (default 'GTC').
    
    Returns:
    - Dict with response information.
    """
    logger.info(f"Preparing order: {side} {quantity} {symbol} ({order_type})")
    
    # 1. Validate inputs
    try:
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
    except ValueError as e:
        err_msg = f"Input validation failed: {e}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # 2. Build parameter dictionary for Binance API
    params = {
        "symbol": validated["symbol"],
        "side": validated["side"],
        "type": validated["type"],
        "quantity": validated["quantity"]
    }
    
    if validated["type"] == "LIMIT":
        params["price"] = validated["price"]
        params["timeInForce"] = time_in_force
        
    elif validated["type"] == "STOP_MARKET":
        params["stopPrice"] = validated["stopPrice"]
        # Note: STOP_MARKET orders typically trigger a market buy/sell.
        # It's recommended to set closePosition=false unless explicitly wanted.
        
    # 3. Send request via client
    logger.info(f"Sending order request: {params['side']} {params['quantity']} {params['symbol']} [{params['type']}]")
    
    try:
        response = client.request("POST", "/fapi/v1/order", params=params, signed=True)
        
        # Log success
        order_id = response.get("orderId")
        status = response.get("status")
        executed_qty = response.get("executedQty", "0.0")
        avg_price = response.get("avgPrice", "0.0")
        
        logger.info(f"Order placed successfully! OrderID: {order_id}, Status: {status}, ExecutedQty: {executed_qty}, AvgPrice: {avg_price}")
        return response
        
    except BinanceAPIError as e:
        logger.error(f"Binance API returned error: Code {e.code} - {e.message}")
        raise
    except BinanceNetworkError as e:
        logger.error(f"Network error while placing order: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while placing order: {e}")
        raise
