import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Import bot components
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.orders import place_order
from bot.validators import validate_all

# Set up page configurations
st.set_page_config(
    page_title="Binance Futures Testnet Bot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply sleek styling adjustments
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #1e222d;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #00c896;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #1a1e28;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #2e3344;
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Initialize session state variables
if "api_key" not in st.session_state:
    st.session_state["api_key"] = os.getenv("BINANCE_API_KEY", "")
if "api_secret" not in st.session_state:
    st.session_state["api_secret"] = os.getenv("BINANCE_API_SECRET", "")
if "refresh_counter" not in st.session_state:
    st.session_state["refresh_counter"] = 0

# Sidebar Configuration
st.sidebar.title("🔐 API Credentials")
st.sidebar.caption("Binance Futures USDT-M Testnet")

input_key = st.sidebar.text_input("API Key", value=st.session_state["api_key"], type="password")
input_secret = st.sidebar.text_input("API Secret", value=st.session_state["api_secret"], type="password")

if input_key != st.session_state["api_key"] or input_secret != st.session_state["api_secret"]:
    st.session_state["api_key"] = input_key
    st.session_state["api_secret"] = input_secret
    st.session_state["refresh_counter"] += 1

# Check credential status
has_creds = bool(st.session_state["api_key"]) and bool(st.session_state["api_secret"])
if has_creds:
    st.sidebar.success("Credentials Loaded!")
else:
    st.sidebar.warning("Please provide API credentials to trade.")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Sync/Refresh Data"):
    st.session_state["refresh_counter"] += 1

# Instantiate client if credentials available
client = None
if has_creds:
    try:
        client = BinanceFuturesClient(
            api_key=st.session_state["api_key"],
            api_secret=st.session_state["api_secret"]
        )
    except Exception as e:
        st.sidebar.error(f"Initialization error: {e}")

# Header
st.title("⚡ Binance Futures Testnet Trading Bot")
st.caption("A premium trading interface for USDT-M Futures Testnet. Built with Streamlit, Python & Requests.")

# Dashboard Body
if client:
    # Fetch account and position details
    try:
        with st.spinner("Fetching account balance and active positions..."):
            account_info = client.get_account_info()
            positions_data = client.get_position_risk()
            open_orders = client.get_open_orders()
            
        # 1. Balance Metrics Row
        st.subheader("💰 Account Summary")
        
        # Calculate key metrics
        wallet_balance = float(account_info.get("totalWalletBalance", 0.0))
        unrealized_pnl = float(account_info.get("totalUnrealizedProfit", 0.0))
        margin_balance = float(account_info.get("totalMarginBalance", 0.0))
        available_balance = 0.0
        
        # Find USDT asset available balance
        assets = account_info.get("assets", [])
        for asset in assets:
            if asset.get("asset") == "USDT":
                available_balance = float(asset.get("availableBalance", 0.0))
                break
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Wallet Balance", f"{wallet_balance:,.2f} USDT")
        col2.metric("Unrealized Profit", f"{unrealized_pnl:,.2f} USDT", delta=f"{unrealized_pnl:+.2f} USDT")
        col3.metric("Margin Balance", f"{margin_balance:,.2f} USDT")
        col4.metric("Available Balance", f"{available_balance:,.2f} USDT")
        
        st.markdown("---")
        
        # 2. Columns layout: Order Placement (Left) vs Active Positions/Orders (Right)
        left_col, right_col = st.columns([1, 1.3])
        
        with left_col:
            st.subheader("📝 Place New Order")
            with st.form("order_form", clear_on_submit=False):
                # Common inputs
                symbol = st.text_input("Symbol", value="BTCUSDT").upper().strip()
                side = st.selectbox("Side", ["BUY", "SELL"])
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP_MARKET"])
                quantity = st.number_input("Quantity", min_value=0.0, step=0.001, format="%.4f")
                
                # Order Type Specific inputs
                price = None
                if order_type == "LIMIT":
                    price = st.number_input("Limit Price", min_value=0.0, step=0.01, format="%.2f")
                
                stop_price = None
                if order_type == "STOP_MARKET":
                    stop_price = st.number_input("Stop Price (Trigger)", min_value=0.0, step=0.01, format="%.2f")
                
                time_in_force = "GTC"
                if order_type == "LIMIT":
                    time_in_force = st.selectbox("Time In Force", ["GTC", "IOC", "FOK"])
                
                submit_order = st.form_submit_button("🚀 Submit Order")
                
                if submit_order:
                    try:
                        # Place order
                        res = place_order(
                            client=client,
                            symbol=symbol,
                            side=side,
                            order_type=order_type,
                            quantity=quantity,
                            price=price,
                            stop_price=stop_price,
                            time_in_force=time_in_force
                        )
                        st.success(f"Order Placed Successfully! ID: {res.get('orderId')}")
                        
                        # Detailed output
                        with st.expander("Order Response Details", expanded=True):
                            st.json({
                                "orderId": res.get("orderId"),
                                "status": res.get("status"),
                                "executedQty": res.get("executedQty"),
                                "avgPrice": res.get("avgPrice"),
                                "type": res.get("type"),
                                "side": res.get("side"),
                                "cumQuote": res.get("cumQuote")
                            })
                        
                        # Force refresh data
                        st.session_state["refresh_counter"] += 1
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Order Placement Failed: {e}")
            
        with right_col:
            # Active Positions Tab and Open Orders Tab
            tab1, tab2 = st.tabs(["📊 Active Positions", "⏳ Open Orders"])
            
            with tab1:
                # Filter positions that have size != 0
                active_positions = []
                for pos in positions_data:
                    amt = float(pos.get("positionAmt", 0.0))
                    if amt != 0.0:
                        active_positions.append({
                            "Symbol": pos.get("symbol"),
                            "Amount": amt,
                            "Entry Price": float(pos.get("entryPrice", 0.0)),
                            "Mark Price": float(pos.get("markPrice", 0.0)),
                            "Unrealized PnL (USDT)": float(pos.get("unrealizedProfit", 0.0)),
                            "Leverage": f"{pos.get('leverage')}x",
                            "Margin Type": "Isolated" if pos.get("isolated") else "Cross"
                        })
                
                if active_positions:
                    df_pos = pd.DataFrame(active_positions)
                    st.dataframe(df_pos, use_container_width=True, hide_index=True)
                else:
                    st.info("No active positions found.")
                    
            with tab2:
                if open_orders:
                    # Cancel order handler
                    orders_list = []
                    for o in open_orders:
                        orders_list.append({
                            "Order ID": o.get("orderId"),
                            "Symbol": o.get("symbol"),
                            "Side": o.get("side"),
                            "Type": o.get("type"),
                            "Qty": float(o.get("origQty", 0.0)),
                            "Price": float(o.get("price", 0.0)),
                            "Stop Price": float(o.get("stopPrice", 0.0))
                        })
                    
                    df_orders = pd.DataFrame(orders_list)
                    st.dataframe(df_orders, use_container_width=True, hide_index=True)
                    
                    # Order cancellation control
                    st.write("---")
                    st.markdown("##### Cancel an Order")
                    cancel_col_symbol, cancel_col_id, cancel_btn_col = st.columns([1, 1, 1])
                    with cancel_col_symbol:
                        cancel_symbol = st.selectbox("Select Symbol to Cancel", list(set(df_orders["Symbol"])))
                    with cancel_col_id:
                        filtered_ids = df_orders[df_orders["Symbol"] == cancel_symbol]["Order ID"].tolist()
                        cancel_id = st.selectbox("Select Order ID to Cancel", filtered_ids)
                    with cancel_btn_col:
                        st.write("") # Spacer
                        st.write("") # Spacer
                        if st.button("❌ Cancel Order"):
                            try:
                                client.cancel_order(cancel_symbol, cancel_id)
                                st.success(f"Cancelled Order {cancel_id}")
                                time.sleep(1)
                                st.session_state["refresh_counter"] += 1
                                st.rerun()
                            except Exception as e:
                                st.error(f"Cancel failed: {e}")
                else:
                    st.info("No open orders found.")

    except BinanceAPIError as e:
        st.error(f"Binance API Error: Code {e.code} - {e.message}")
        st.info("Ensure your API Key and Secret are correct and have futures trading enabled.")
    except BinanceNetworkError as e:
        st.error(f"Network error connecting to Binance: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
else:
    st.info("👈 Enter your Binance Futures Testnet API Key and API Secret in the sidebar to begin.")

# 3. Log Viewer Section
st.markdown("---")
st.subheader("📋 Log Viewer (`trading_bot.log`)")
log_file = "trading_bot.log"
if os.path.exists(log_file):
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            log_lines = f.readlines()
        
        # Grab the last 40 lines of logs
        last_logs = "".join(log_lines[-40:])
        st.code(last_logs, language="log")
    except Exception as e:
        st.error(f"Failed to read log file: {e}")
else:
    st.caption("No log file found yet. Place some orders or run actions to populate logs.")
