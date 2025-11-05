import gc                       # Garbage collection
import os                       # Operating system interface
import json                     # JSON handling
import asyncio                  # Asynchronous I/O
import traceback                # Exception handling
import pandas as pd             # Data analysis library
import math                     # Mathematical functions

import poly_data.global_state as global_state
import poly_data.CONSTANTS as CONSTANTS

# Import utility functions for trading
from poly_data.trading_utils import get_best_bid_ask_deets, get_order_prices, get_buy_sell_amount, get_top_ask, get_top_bid, round_down, round_up, get_size_by_token_id_price
from poly_data.data_utils import get_order, has_order, set_order, set_size, get_size

# Create directory for storing position risk information
if not os.path.exists('positions/'):
    os.makedirs('positions/')

def send_order(order):
    print("send_buy_order called with order:", order)
    client = global_state.client
    print(f'Ordering {order['token']} to {order['side']} {order["size"]} shares at ${order["price"]}')

    if order['side'] == 'BUY' and (order['price'] < 0.1 or order['price'] > 0.9):
        print
        return
    
    if CONSTANTS.DEBUG_MODE:
        print("DEBUG mode is ON. Order not sent.")
        return  
    
    client = global_state.client
    client.create_order(
        order['token'], 
        order['side'], 
        order['price'], 
        order['size'], 
        True if order['neg_risk'] == 'TRUE' else False
    )

def trade_token(token, side, price, size, neg_risk):
    print(f'Ordering {token} to {side} {size} shares at ${price}')

    if side == 'BUY' and (price < 0.1 or price > 0.9):
        print("Buy order price out of bounds. Skipping.")
        return

    order = {
        "token": token,
        "side": side,
        "price": price,
        "size": size,
        "neg_risk": True if neg_risk == 'TRUE' else False
    }    
    send_order(order)
    order = set_order(order)

# Dictionary to store locks for each market to prevent concurrent trading on the same market
market_locks = {}
    
async def perform_trade(market):
    """
    Main trading function that handles market making for a specific market.
    
    This function:
    1. Merges positions when possible to free up capital
    2. Analyzes the market to determine optimal bid/ask prices
    3. Manages buy and sell orders based on position size and market conditions
    4. Implements risk management with stop-loss and take-profit logic
    
    Args:
        market (str): The market ID to trade on
    """
    # Create a lock for this market if it doesn't exist
    if market not in market_locks:
        market_locks[market] = asyncio.Lock()

    # Use lock to prevent concurrent trading on the same market
    async with market_locks[market]:
        try:
            data = {} 

            client = global_state.client
            # Get market details from the configuration
            row = global_state.df[global_state.df['condition_id'] == market].iloc[0]      
            # Determine decimal precision from tick size
            round_length = len(str(row['tick_size']).split(".")[1])
            data['round_length'] = round_length

            # Get trading parameters for this market type
            params = global_state.params[row['param_type']]
            
            # Create a list with both outcomes for the market
            deets = [
                {'name': 'token1', 'token': row['token1'], 'answer': row['answer1']}, 
                {'name': 'token2', 'token': row['token2'], 'answer': row['answer2']}
            ]
            print(f"\n\n{pd.Timestamp.utcnow().tz_localize(None)}: {row['question']}")

            # Loop through both outcomes in the market (YES and NO)
            for detail in deets:
                token = str(detail['token'])
                
                # Extract all order book details
                top_bid = get_top_bid(token)
                top_ask = get_top_ask(token)

                if top_bid is None or top_ask is None:
                    print(f"Top bid or ask is None for token {token}. Skipping.")
                    continue
                top_bid = round(top_bid, round_length)
                top_ask = round(top_ask, round_length)
                for i in range(90, 10, -1):
                    price = i / 100.0

                    if price < top_ask:
                        # print(f"Price {price} below top ask {top_ask}, buy order {token}") 
                        side = 'BUY' 
                        if not has_order(token, side, price):
                            size = get_size_by_token_id_price(token, side, price, row['trade_size'])
                            if size > 0:
                                trade_token(token, side, price, size, row['neg_risk'])
        except Exception as ex:
            print(f"Error performing trade for {market}: {ex}")
            traceback.print_exc()

        # Clean up memory and introduce a small delay
        gc.collect()

        await asyncio.sleep(2)
