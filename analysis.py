from tradingview_ta import TA_Handler

from request_functions import get_candlestick_data, get_long_short_volume
from utility import convert_usdt_symbol


# #Trade Candle Strategy - Overlapping
# def trade_overlapping(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT):
#     data = get_candlestick_data(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT)
#     if data == None:
#         return None
#
#     else:

#Trade Candle Strategy - Spike
#Buy
#После красного спайка (фитиль > тела) - зеленая свеча, которая закрывается выше открытия спайка
#Индикаторы ТА - Buy


def buy_sell_ratio_analysis(symbol, period='5m'):
    symbol = convert_usdt_symbol(symbol)
    response1 = get_long_short_volume(symbol, period=period)
    if not response1:
        print("No long_short_volume found!")
        return None
    else:
        buy_volume = float(response1.json()['data'][-1]['buyVolume'])
        sell_volume = float(response1.json()['data'][-1]['sellVolume'])
        if (buy_volume + sell_volume) > 0:
            buy_rate = (buy_volume / (buy_volume + sell_volume)) * 100
            sell_rate = (sell_volume / (buy_volume + sell_volume)) * 100

            if buy_rate > sell_rate:
                return "SELL"
            elif buy_rate < sell_rate:
                return "BUY"
            else:
                return "NEUTRAL"
        else:
            print(f"buy_volume + sell_volume = 0 or < 0!"
                  f"buy_volume: {buy_volume}, sell_volume: {sell_volume}")
            return None



def trade_candlestick_analysis(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT):
    data = get_candlestick_data(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT)
    if not data:
        return None

    else:
        # Three candles pattern
        # 1st candle data
        # open = data[0][1]
        # high = data[0][2]
        # low = data[0][3]
        # close = data[0][4]

        # Buy
        if data[0][1] < data[0][4] and (data[0][4] - data[0][1]) > max((data[0][2] - data[0][4]), (data[0][1] - data[0][3])):
            if data[1][1] < data[1][4] and (data[1][4] - data[1][1]) > max((data[1][2] - data[1][4]), (data[1][1] - data[1][3])):
                if data[1][4] > data[0][4] and data[1][3] > data[0][3]:
                    return 'BUY'

        # Sell
        if data[0][1] > data[0][4] and (data[0][1] - data[0][4]) > max((data[0][2] - data[0][1]),
                                                                       (data[0][4] - data[0][3])):
            if data[1][1] > data[1][4] and (data[1][1] - data[1][4]) > max((data[1][2] - data[1][1]),
                                                                           (data[1][4] - data[1][3])):
                if data[1][4] < data[0][4] and data[1][3] < data[0][3]:
                    return 'SELL'
        #Neutral
        elif ((data[1][1] > data[1][4] and (data[1][1] - data[1][4]) * 2 < (data[1][2] - data[1][1])) and
              ((data[1][1] - data[1][4]) * 2 < (data[1][4] - data[1][3]))
              or
              (data[1][1] < data[1][4] and (data[1][4] - data[1][1]) * 2 < (data[1][2] - data[1][4])) and
              ((data[1][4] - data[1][1]) * 2 < (data[1][1] - data[1][3]))):
            return "NEUTRAL"
        else:
            return None









# def trade_candlestick_analysis(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT):
#     data = get_candlestick_data(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT)
#     if not data:
#         return None
#
#     else:
#         # Three candles pattern
#         # 1st candle data
#         # open = data[0][1]
#         # high = data[0][2]
#         # low = data[0][3]
#         # close = data[0][4]
#
#
#
#         # Buy
#         if data[0][1] > data[0][4] and \
#                 (data[0][1] - data[0][4]) > 1.5 * max((data[0][2] - data[0][1]), (data[0][4] - data[0][3])):
#             if (data[1][1] > data[1][4] and (data[1][1] - data[1][4]) * 1.5 < (data[1][4] - data[1][3])) or \
#                     (data[1][1] < data[1][4] and (data[1][4] - data[1][1]) * 1.5 < (data[1][1] - data[1][3])):
#                 if data[2][1] < data[2][4] and data[2][4] > max(data[1][1], data[1][4]):
#                     return 'BUY'
#
#         # Sell
#         elif data[0][1] < data[0][4] and \
#                 (data[0][4] - data[0][1]) > 1.5 * max((data[0][2] - data[0][4]), (data[0][1] - data[0][3])):
#             if (data[1][1] > data[1][4] and (data[1][1] - data[1][4]) * 1.5 < (data[1][2] - data[1][1])) or \
#                     (data[1][1] < data[1][4] and (data[1][4] - data[1][1]) * 1.5 < (data[1][2] - data[1][4])):
#                 if data[2][1] > data[2][4] and data[2][4] < min(data[1][1], data[1][4]):
#                     return 'SELL'
#         #Neutral
#         elif ((data[1][1] > data[1][4] and (data[1][1] - data[1][4]) * 2 < (data[1][2] - data[1][1])) and
#               ((data[1][1] - data[1][4]) * 2 < (data[1][4] - data[1][3]))
#               or
#               (data[1][1] < data[1][4] and (data[1][4] - data[1][1]) * 2 < (data[1][2] - data[1][4])) and
#               ((data[1][4] - data[1][1]) * 2 < (data[1][1] - data[1][3]))):
#             return "NEUTRAL"
#         else:
#             return None


#Tradingview summary analysis
def trade_tradingview_ta(SYMBOL, EXCHANGE, INTERVAL):
    try:
        handler = TA_Handler(symbol=convert_usdt_symbol(SYMBOL),
                             screener='Crypto',
                             exchange=EXCHANGE,
                             interval=INTERVAL
                             )

        recommendation = handler.get_analysis().summary["RECOMMENDATION"]
        return recommendation
    except Exception as e:
        # Handle specific custom exception
        if str(e) == "Exchange or symbol not found.":
            print(f"Custom exception caught: {e}{SYMBOL}")
        else:
            print(f"Error processing symbol {SYMBOL}: {e}")
        return None
