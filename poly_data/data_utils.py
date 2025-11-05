import poly_data.global_state as global_state
from poly_data.utils import get_sheet_df
import time
import poly_data.global_state as global_state

#sth here seems to be removing the position
def update_positions(avgOnly=False):
    pos_df = global_state.client.get_all_positions()

    for idx, row in pos_df.iterrows():
        asset = str(row['asset'])

        if asset in  global_state.positions:
            position = global_state.positions[asset].copy()
        else:
            position = {'size': 0, 'avgPrice': 0}

        position['avgPrice'] = row['avgPrice']

        if not avgOnly:
            position['size'] = row['size']
        else:
            
            for col in [f"{asset}_sell", f"{asset}_buy"]:
                #need to review this
                if col not in global_state.performing or not isinstance(global_state.performing[col], set) or len(global_state.performing[col]) == 0:
                    try:
                        old_size = position['size']
                    except:
                        old_size = 0

                    if asset in  global_state.last_trade_update:
                        if time.time() - global_state.last_trade_update[asset] < 5:
                            print(f"Skipping update for {asset} because last trade update was less than 5 seconds ago")
                            continue

                    if old_size != row['size']:
                        print(f"No trades are pending. Updating position from {old_size} to {row['size']} and avgPrice to {row['avgPrice']} using API")
    
                    position['size'] = row['size']
                else:
                    print(f"ALERT: Skipping update for {asset} because there are trades pending for {col} looking like {global_state.performing[col]}")
    
        global_state.positions[asset] = position


def get_size(token, side, price):
    if token not in global_state.size or side not in global_state.size[token] or price not in global_state.size[token][side]:
        return 0
    return global_state.size[token][side][price]
    
def set_size(token, side, size, price):
    if token not in global_state.size:
        global_state.size[token] = {} 
    if side not in global_state.size[token]: 
        global_state.size[token][side] = {}
    if price not in global_state.size[token][side]:
        global_state.size[token][side][price] = 0
    global_state.size[token][side][price] = size
    print(f"Updated size from {token}, set to ", global_state.size[token][side][price])

def has_order(token, side, price):
    if token not in global_state.order or side not in global_state.order[token] or price not in global_state.order[token][side]:
        return False
    return True

def get_order(token, side, price):
    if token not in global_state.order or side not in global_state.order[token] or price not in global_state.order[token][side]:
        return None
    return global_state.order[token][side][price]
    
def set_order(order):
    token = order['token']
    size = order['size']
    side = order['side']
    price = order['price']
    print(f"Order for token {token} {side} {size} shares at ${price}")

    if token not in global_state.order:
        global_state.order[token] = {}
    if side not in global_state.order[token]: 
        global_state.order[token][side] = {}
    if price not in global_state.order[token][side]:
        global_state.order[token][side][price] = 0
    global_state.order[token][side][price] = order 

def update_orders():
    all_orders = global_state.client.get_all_orders()

    orders = {}

    for i, row in all_orders.iterrows():
        token = int(row['asset_id'])
        side = row['side'].upper()
        price = float(row['price'])
        original_size = float(row['original_size'])
        size = float(row['original_size']) - float(row['size_matched'])
        order = {
            'token': token,
            'side': side,
            'price': price,
            'size': size,
            'original_size': original_size
        }
        # set_size(token, side, original_size, price)
        set_order(order)

    print("Updated orders from API:", orders)
    global_state.orders = orders

def update_markets():
    received_df, received_params = get_sheet_df()
    # print("Length of received_df", len(received_df))

    if len(received_df) > 0:
        global_state.df, global_state.params = received_df.copy(), received_params
    
    # print("Length of global_state", len(global_state.df))

    for _, row in global_state.df.iterrows():
        for col in ['token1', 'token2']:
            row[col] = str(row[col])

        if row['token1'] not in global_state.all_tokens:
            global_state.all_tokens.append(row['token1'])
        if row['token2'] not in global_state.all_tokens:
            global_state.all_tokens.append(row['token2'])

        if row['token1'] not in global_state.REVERSE_TOKENS:
            global_state.REVERSE_TOKENS[row['token1']] = row['token2']

        if row['token2'] not in global_state.REVERSE_TOKENS:
            global_state.REVERSE_TOKENS[row['token2']] = row['token1']

        for col2 in [f"{row['token1']}_buy", f"{row['token1']}_sell", f"{row['token2']}_buy", f"{row['token2']}_sell"]:
            if col2 not in global_state.performing:
                global_state.performing[col2] = set()