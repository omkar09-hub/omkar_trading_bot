import os
import sys
import argparse
from dotenv import load_dotenv

# Import rich components for premium terminal output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

# Import bot components
from bot.logging_config import logger
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceClientError
from bot.orders import place_order
from bot.validators import validate_symbol, validate_side, validate_order_type, validate_quantity, validate_price, validate_stop_price

# Load environment variables
load_dotenv()

console = Console()

def get_credentials(args):
    """
    Retrieves API Key and Secret from arguments or environment variables.
    """
    api_key = args.api_key or os.getenv("BINANCE_API_KEY")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET")
    return api_key, api_secret

def print_banner():
    """
    Prints a beautiful header banner for the trading bot.
    """
    console.print(Panel.fit(
        "[bold green]=== Binance Futures Trading Bot ===[/bold green]\n"
        "[dim]USDT-M Futures Testnet Client - Premium Edition[/dim]",
        border_style="green",
        subtitle="Primetrade.ai Hiring Task"
    ))

def execute_order_flow(client, symbol, side, order_type, quantity, price, stop_price):
    """
    Helper function to validate, run order, and print rich responses.
    """
    # Print Order Request Summary
    summary_table = Table(title="[bold cyan]Order Request Summary[/bold cyan]", show_header=False)
    summary_table.add_row("Symbol", symbol)
    summary_table.add_row("Side", f"[green]BUY[/green]" if side.upper() == "BUY" else "[red]SELL[/red]")
    summary_table.add_row("Type", order_type)
    summary_table.add_row("Quantity", str(quantity))
    if order_type.upper() == "LIMIT":
        summary_table.add_row("Price", str(price))
    elif order_type.upper() == "STOP_MARKET":
        summary_table.add_row("Stop Price", str(stop_price))
        
    console.print(summary_table)
    console.print("\n[yellow]Placing order...[/yellow]")
    
    try:
        response = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        # Display response details
        resp_table = Table(title="[bold green][SUCCESS] Order Placed Successfully![/bold green]", show_header=False)
        resp_table.add_row("Order ID", str(response.get("orderId")))
        resp_table.add_row("Status", str(response.get("status")))
        resp_table.add_row("Executed Qty", str(response.get("executedQty", "0.0")))
        resp_table.add_row("Avg Price", str(response.get("avgPrice", "0.0")))
        resp_table.add_row("Cumulative Quote", str(response.get("cumQuote", "0.0")))
        
        console.print(Panel(resp_table, border_style="green"))
        
    except BinanceAPIError as e:
        console.print(Panel(
            f"[bold red][API ERROR] Binance API Error![/bold red]\n"
            f"[bold]Error Code:[/bold] {e.code}\n"
            f"[bold]Message:[/bold] {e.message}\n"
            f"[bold]HTTP Status:[/bold] {e.status_code}",
            title="Execution Failed",
            border_style="red"
        ))
    except BinanceNetworkError as e:
        console.print(Panel(
            f"[bold red][NETWORK ERROR] Network Failure![/bold red]\n"
            f"Could not connect to Binance server: {e}",
            title="Connection Error",
            border_style="red"
        ))
    except Exception as e:
        console.print(Panel(
            f"[bold red][ERROR] Validation or Unexpected Error![/bold red]\n"
            f"{e}",
            title="Error",
            border_style="red"
        ))

def run_interactive_mode(client):
    """
    Launches interactive menu for CLI user.
    """
    while True:
        console.print("\n[bold cyan]Menu Options:[/bold cyan]")
        console.print("1. [green]Place Market Order[/green]")
        console.print("2. [yellow]Place Limit Order[/yellow]")
        console.print("3. [magenta]Place Stop-Market Order[/magenta]")
        console.print("4. [cyan]View Open Orders[/cyan]")
        console.print("5. [red]Cancel Open Order[/red]")
        console.print("6. [dim]Show Server Time Offset[/dim]")
        console.print("7. Exit")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7"], default="7")
        
        if choice == "7":
            console.print("[yellow]Exiting trading bot. Goodbye![/yellow]")
            break
            
        if choice in ["1", "2", "3"]:
            # Gather inputs with validation
            order_type = "MARKET" if choice == "1" else "LIMIT" if choice == "2" else "STOP_MARKET"
            
            # Symbol
            while True:
                symbol = Prompt.ask("Enter Symbol (e.g. BTCUSDT)", default="BTCUSDT")
                try:
                    symbol = validate_symbol(symbol)
                    break
                except ValueError as e:
                    console.print(f"[red]{e}[/red]")
            
            # Side
            side = Prompt.ask("Enter Side", choices=["BUY", "SELL"], default="BUY")
            
            # Quantity
            while True:
                quantity = Prompt.ask("Enter Quantity")
                try:
                    quantity = validate_quantity(quantity)
                    break
                except ValueError as e:
                    console.print(f"[red]{e}[/red]")
            
            # Price (for LIMIT)
            price = None
            if order_type == "LIMIT":
                while True:
                    price = Prompt.ask("Enter Limit Price")
                    try:
                        price = validate_price(price, order_type)
                        break
                    except ValueError as e:
                        console.print(f"[red]{e}[/red]")
            
            # Stop Price (for STOP_MARKET)
            stop_price = None
            if order_type == "STOP_MARKET":
                while True:
                    stop_price = Prompt.ask("Enter Stop Trigger Price")
                    try:
                        stop_price = validate_stop_price(stop_price, order_type)
                        break
                    except ValueError as e:
                        console.print(f"[red]{e}[/red]")
            
            # Execute Order Flow
            execute_order_flow(client, symbol, side, order_type, quantity, price, stop_price)
            
        elif choice == "4":
            symbol_filter = Prompt.ask("Enter Symbol to filter (press Enter for all)", default="")
            symbol_val = symbol_filter.strip().upper() if symbol_filter else None
            try:
                orders = client.get_open_orders(symbol=symbol_val)
                if not orders:
                    console.print("[yellow]No open orders found.[/yellow]")
                else:
                    table = Table(title="Active Open Orders")
                    table.add_column("Order ID")
                    table.add_column("Symbol")
                    table.add_column("Side")
                    table.add_column("Type")
                    table.add_column("Qty")
                    table.add_column("Price")
                    table.add_column("Stop Price")
                    
                    for o in orders:
                        table.add_row(
                            str(o["orderId"]),
                            o["symbol"],
                            f"[green]{o['side']}[/green]" if o["side"] == "BUY" else f"[red]{o['side']}[/red]",
                            o["type"],
                            str(o["origQty"]),
                            str(o["price"]),
                            str(o.get("stopPrice", "0.0"))
                        )
                    console.print(table)
            except Exception as e:
                console.print(f"[red]Error fetching orders: {e}[/red]")
                
        elif choice == "5":
            symbol = Prompt.ask("Enter Order Symbol (e.g. BTCUSDT)")
            order_id = Prompt.ask("Enter Order ID to Cancel")
            try:
                res = client.cancel_order(symbol.strip().upper(), int(order_id.strip()))
                console.print(Panel(f"[green]Successfully Cancelled Order {res['orderId']} ({res['symbol']})[/green]"))
            except Exception as e:
                console.print(f"[red]Error cancelling order: {e}[/red]")
                
        elif choice == "6":
            client.sync_time()
            console.print(f"[cyan]Server offset: {client.time_offset}ms[/cyan]")

def main():
    parser = argparse.ArgumentParser(description="Binance Futures USDT-M Testnet Trading Bot")
    parser.add_argument("--symbol", type=str, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--order-type", type=str, choices=["MARKET", "LIMIT", "STOP_MARKET"], help="Order type")
    parser.add_argument("--quantity", type=float, help="Order quantity")
    parser.add_argument("--price", type=float, help="Limit price (required if order type is LIMIT)")
    parser.add_argument("--stop-price", type=float, help="Trigger price (required if order type is STOP_MARKET)")
    parser.add_argument("--api-key", type=str, help="Binance Testnet API Key")
    parser.add_argument("--api-secret", type=str, help="Binance Testnet API Secret")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive terminal UI")
    
    args = parser.parse_args()
    print_banner()
    
    api_key, api_secret = get_credentials(args)
    
    if not api_key or not api_secret:
        console.print("[bold yellow][WARNING] Warning: Binance Testnet API credentials not found in command line or .env file.[/bold yellow]")
        if not args.interactive and (args.symbol or args.order_type):
            console.print("[bold red]Error: API credentials are required for direct command line order placement. Please supply them via environment variables or CLI options.[/bold red]")
            sys.exit(1)
        # In interactive mode, we will ask the user for them
        api_key = Prompt.ask("Enter Binance Testnet API Key", password=True)
        api_secret = Prompt.ask("Enter Binance Testnet API Secret", password=True)
        
    try:
        # Initialize Client
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except Exception as e:
        console.print(f"[bold red]Failed to initialize Binance Client: {e}[/bold red]")
        sys.exit(1)
        
    # Check if we should run in interactive mode
    if args.interactive or (not args.symbol and not args.order_type):
        console.print("[cyan]No order arguments provided. Launching interactive console menu...[/cyan]")
        run_interactive_mode(client)
    else:
        # Check required CLI arguments for placing an order
        if not args.symbol or not args.side or not args.order_type or args.quantity is None:
            console.print("[bold red]Error: For direct execution, you must supply --symbol, --side, --order-type, and --quantity.[/bold red]")
            sys.exit(1)
            
        execute_order_flow(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price
        )

if __name__ == "__main__":
    main()
