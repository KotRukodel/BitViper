from request_functions import get_account_info, get_symbol_price, get_candlestick_data
from telegram_bot import bot_send_message
from utility import convert_price_to_symbol, check_min_max_lot

# Count SL and TP for position according to the side of trade (PREDICT)
def sl_tp_count(RR, SYMBOL, PRODUCTTYPE, GRANULARITY, LIMIT, PREDICT):
    sl, tp, delta_SL = "", "", ""
    data = get_candlestick_data(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT)
    price_response = get_symbol_price(SYMBOL, PRODUCTTYPE).json()

    if 'data' not in price_response or not price_response['data'] or not data:
        print(f"Can't sl_tp_count for {SYMBOL} as no price_response or candlestick_data!")
        #sl, tp, delta_SL = "", "", ""
        return sl, tp, delta_SL

    cur_price = float(price_response['data'][0]['price'])
    recommend = PREDICT

    candles_prices = [candle[i] for candle in data for i in range(1, 4)]

    if recommend == "BUY":
        sl = min(candles_prices)
        if sl < cur_price:
            delta_SL = cur_price - sl
            delta_TP = delta_SL * RR
            tp = convert_price_to_symbol(PRODUCTTYPE, SYMBOL, cur_price + delta_TP)
            if tp > cur_price:
                print("SL and TP are successfully counted!\n"
                      f"Symbol: {SYMBOL}, Side: {recommend}, SL: {sl}, TP:{tp}, Delta_SL: {round(delta_SL, 5)}")
                bot_send_message("SL and TP are successfully counted!\n"
                                 f"Symbol: {SYMBOL}, Side: {recommend}, SL: {sl}, TP:{tp}, Delta_SL: {round(delta_SL, 5)}")
                return sl, tp, delta_SL
    elif recommend == "SELL":
        sl = max(candles_prices)
        if sl > cur_price:
            delta_SL = sl - cur_price
            delta_TP = delta_SL * RR
            tp = convert_price_to_symbol(PRODUCTTYPE, SYMBOL, cur_price - delta_TP)
            if tp < cur_price:
                print("SL and TP are successfully counted!\n"
                      f"Symbol: {SYMBOL}, Side: {recommend}, SL: {sl}, TP:{tp}, Delta_SL: {round(delta_SL, 5)}")
                bot_send_message("SL and TP are successfully counted!\n"
                                 f"Symbol: {SYMBOL}, Side: {recommend}, SL: {sl}, TP:{tp}, Delta_SL: {round(delta_SL, 5)}")
                return sl, tp, delta_SL

    print(f"No sl_tp for {SYMBOL} as logic is incorrect!\n"
          f"Cur_price: {cur_price}, SL: {sl}, TP: {tp}")
    bot_send_message(f"No sl_tp for {SYMBOL} as logic is incorrect!\n"
                     f"Cur_price: {cur_price}, SL: {sl}, TP: {tp}")

    return sl, tp, delta_SL


# Count TRADE_RISK amount in USDT
def trade_equity_count(SYMBOL, PRODUCTTYPE, MARGINCOIN, TRADE_RISK):
    try:
        response = get_account_info(PRODUCTTYPE, SYMBOL, MARGINCOIN).json()
        data = response['data']
        if len(data) > 0:
            equity = float(data['available'])
            trade_equity = round(equity * float(TRADE_RISK), 2)
            return trade_equity
        else:
            raise IndexError("Data list for trade_equity_count is empty!")
    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Error processing trade_equity_count for symbol: {SYMBOL} lot : {e}")
        return None


# Count trade lot
def lot_count(SYMBOL, PRODUCTTYPE, SL, DELTA_SL, TRADE_EQUITY, TRADE_RISK, LEVERAGE, PFF):

    if not SL or not DELTA_SL or not TRADE_EQUITY:
        lot = ""
        print(f"Can't count Lot as no SL or Trade Equity for Symbol!"
              f"Symbol: {SYMBOL}, SL: {SL}, TE: {TRADE_EQUITY}")
    else:
        lot = float(TRADE_EQUITY / DELTA_SL)
        #Проверка мин и максимального размера лота, в т.ч. объем в USDT > 5 USDT
        #В т.ч. проверка на соответствие маржинальным требованиям
        lot = check_min_max_lot(PRODUCTTYPE, SYMBOL, lot, TRADE_EQUITY, TRADE_RISK, LEVERAGE, DELTA_SL, PFF)
    return lot





