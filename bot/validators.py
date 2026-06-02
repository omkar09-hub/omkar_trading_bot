import re

def validate_symbol(symbol: str) -> str:
    """
    Validates the trading symbol. Must be uppercase, alphanumeric, e.g., BTCUSDT.
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    
    cleaned_symbol = symbol.strip().upper()
    
    # Check if symbol is alphanumeric and reasonable length
    if not re.match(r'^[A-Z0-9]{3,20}$', cleaned_symbol):
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphanumeric, uppercase, and between 3-20 characters (e.g., BTCUSDT)."
        )
    return cleaned_symbol

def validate_side(side: str) -> str:
    """
    Validates the order side. Must be 'BUY' or 'SELL'.
    """
    if not side:
        raise ValueError("Order side cannot be empty.")
    
    cleaned_side = side.strip().upper()
    if cleaned_side not in ["BUY", "SELL"]:
        raise ValueError(f"Invalid side '{side}'. Must be either 'BUY' or 'SELL'.")
    return cleaned_side

def validate_order_type(order_type: str) -> str:
    """
    Validates the order type. Must be 'MARKET', 'LIMIT', or 'STOP_MARKET'.
    """
    if not order_type:
        raise ValueError("Order type cannot be empty.")
    
    cleaned_type = order_type.strip().upper()
    valid_types = ["MARKET", "LIMIT", "STOP_MARKET"]
    if cleaned_type not in valid_types:
        raise ValueError(f"Invalid order type '{order_type}'. Supported types: {', '.join(valid_types)}.")
    return cleaned_type

def validate_quantity(quantity) -> float:
    """
    Validates the order quantity. Must be a positive number.
    """
    try:
        qty_float = float(quantity)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a numeric value.")
    
    if qty_float <= 0:
        raise ValueError(f"Quantity must be greater than zero. Received: {qty_float}")
    return qty_float

def validate_price(price, order_type: str) -> float:
    """
    Validates price. Required and must be positive if order_type is 'LIMIT'.
    """
    cleaned_type = order_type.strip().upper()
    
    if cleaned_type == "LIMIT":
        if price is None or str(price).strip() == "":
            raise ValueError("Price is required for LIMIT orders.")
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid price '{price}'. Must be a numeric value.")
        
        if price_float <= 0:
            raise ValueError(f"Price must be greater than zero. Received: {price_float}")
        return price_float
    return 0.0

def validate_stop_price(stop_price, order_type: str) -> float:
    """
    Validates stop_price. Required and must be positive if order_type is 'STOP_MARKET'.
    """
    cleaned_type = order_type.strip().upper()
    
    if cleaned_type == "STOP_MARKET":
        if stop_price is None or str(stop_price).strip() == "":
            raise ValueError("Stop price is required for STOP_MARKET orders.")
        try:
            stop_price_float = float(stop_price)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid stop price '{stop_price}'. Must be a numeric value.")
        
        if stop_price_float <= 0:
            raise ValueError(f"Stop price must be greater than zero. Received: {stop_price_float}")
        return stop_price_float
    return 0.0

def validate_all(symbol: str, side: str, order_type: str, quantity, price=None, stop_price=None) -> dict:
    """
    Validates all order inputs together and returns a dictionary of clean validated values.
    Raises ValueError on validation failure.
    """
    valid_symbol = validate_symbol(symbol)
    valid_side = validate_side(side)
    valid_type = validate_order_type(order_type)
    valid_qty = validate_quantity(quantity)
    valid_price = validate_price(price, valid_type)
    valid_stop_price = validate_stop_price(stop_price, valid_type)
    
    return {
        "symbol": valid_symbol,
        "side": valid_side,
        "type": valid_type,
        "quantity": valid_qty,
        "price": valid_price,
        "stopPrice": valid_stop_price
    }
