import asyncio
import datetime
from tradingview_ta import Interval

from analysis import trade_tradingview_ta, trade_candlestick_analysis, buy_sell_ratio_analysis
from request_functions import *
from telegram_bot import *
import time

from utility import convert_usdt_symbol, clear_queue
from websocket import positions_history_last_closed, get_websocket_channel_data


# Make trade
def make_trade(SYMBOL, QTY, PRODUCTTYPE, MARGINCOIN, MARGIN_MODE, MANAGE_POSITION, SL='', TP=''):
    """Доработать открытие в hedge_mode с обязательной передачей параметра tradeSide в place_order!
       При открытии - выводить риск в % и деньгах
       Отслеживание позиции - при закрытии - PNL"""
    if SYMBOL and QTY and MANAGE_POSITION:
        if MANAGE_POSITION == 'open_buy': # and manage_positions ==

            position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "buy",
                                        marginMode=MARGIN_MODE, tp=TP, sl=SL)
            if position_open.status_code == 200 and position_open.json()['msg'] == 'success':
                print(f"New position long is successfully opened!\n"
                      f"Symbol: {SYMBOL}, QTY: {QTY}")
                bot_send_message(f"New position long is successfully opened!\n"
                                 f"Symbol: {SYMBOL}, QTY: {QTY}")
                print(position_open.json())

            else:
                print(position_open.status_code)
                print(position_open.json()['msg'])

        elif MANAGE_POSITION == 'open_sell':

            position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "sell",
                                        marginMode=MARGIN_MODE, tp=TP, sl=SL)
            if position_open.status_code == 200 and position_open.json()['msg'] == 'success':
                print(f"New position short is successfully opened!\n"
                      f"Symbol: {SYMBOL}, QTY: {QTY}")
                bot_send_message(f"New position short is successfully opened!\n"
                                 f"Symbol: {SYMBOL}, QTY: {QTY}")
                print(position_open.json())

            else:
                print(position_open.status_code)
                print(position_open.json()['msg'])

        else:
            print('No conditions for opening position!')
            return None
    else:
        print('No necessary parameters for position:\n'
              f'SYMBOL: {SYMBOL}, QTY: {QTY}, SL: {SL}, TP: {TP}, MANAGE_POSITION: {MANAGE_POSITION}')
        return None


# Manage conditions for close positions
async def manage_position_close(productType, queue, public_queue):
    """Отслеживание позиции
       PNL текущей позиции
       Отслеживание результата закрытой позиции"""

    EXCHANGE = "BITGET"
    INTERVAL = Interval.INTERVAL_1_MINUTE

    GRANULARITY = '1m'
    LIMIT = '4'

    SLEEP_TIME = 10

    opened_positions = {}
    closed_positions = []

    while True:
        while not queue.empty():
            websocket_msg_private = await queue.get()
            if websocket_msg_private['arg']['channel'] == 'positions':
                print(f"Received data POSITIONS: {websocket_msg_private}")

                positions = await get_websocket_channel_data(websocket_msg_private, 'positions')
                if positions:
                    for position in positions:
                        position_id = position['instId']
                        if float(position['available']) > 0:
                            opened_positions[position_id] = position
                        else:
                            if position_id in opened_positions:
                                closed_positions.append(opened_positions.pop(position_id))

        # Обработка открытых позиций
        if opened_positions:
            for position_id, position in opened_positions.items():
                position_symbol = position['instId']
                position_side = position['holdSide']
                position_qty = float(position['total'])
                position_pnl = round(float(position['unrealizedPL']), 2)
                position_liq_price = round(float(position['liquidationPrice']), 2)
                position_breakeven = float(position['breakEvenPrice'])
                # position_liq_price = round(float(position['liquidationPrice']), 2)
                # position_marginsize = position['marginSize']
                # position_marginmode = position['marginMode']

                if not public_queue.empty():
                    await clear_queue(public_queue)
                    await asyncio.sleep(0.1)

                    websocket_msg_public = await public_queue.get()
                    if websocket_msg_public['arg']['channel'] == 'ticker' and \
                       websocket_msg_public['data'][0]['instId'] == position_id:

                        unix_time = int(websocket_msg_public['data'][0]['ts']) / 1000
                        print(f"UNIX time: {unix_time}")
                        # Преобразование времени UNIX в объект datetime
                        dt_object = datetime.datetime.fromtimestamp(unix_time)
                        # Преобразование объекта datetime в строку в формате чч:мм:сс
                        time_str = dt_object.strftime('%H:%M:%S')
                        local_time = datetime.datetime.now()

                        print(f"Received data MARKET: {websocket_msg_public}\n"
                              f"TimeStamp: {time_str}\n"
                              f"LocalTime: {local_time}")

                        position_symbol_data = await get_websocket_channel_data(websocket_msg_public, 'ticker')
                        if position_symbol_data:
                            symbol_last_price = float(position_symbol_data[0]['lastPr'])
                            position_pnl = round((symbol_last_price - position_breakeven) * position_qty, 2)

                ta_result = trade_tradingview_ta(position_symbol, EXCHANGE, INTERVAL)
                candle_ta_result = trade_candlestick_analysis(productType, position_symbol, GRANULARITY,
                                                              LIMIT)
                buy_sell_ratio_predict = buy_sell_ratio_analysis(position_symbol)

                if ta_result and candle_ta_result:
                    if "BUY" in ta_result and candle_ta_result == "BUY" and position_side == 'short':
                        await close_position(productType, position_symbol, 'short', SLEEP_TIME)
                    elif "SELL" in ta_result and candle_ta_result == "SELL" and position_side == 'long':
                        await close_position(productType, position_symbol, 'long', SLEEP_TIME)
                    else:
                        print_position(position_symbol, position_qty, position_pnl, position_side,
                                       position_liq_price)
                else:
                    print(f"No tradingview_analysis for {position_symbol}!\n")
                    bot_send_message(f"No tradingview_analysis for {position_symbol}!\n")

                    if buy_sell_ratio_predict == "BUY" and candle_ta_result == "BUY" and position_side == 'short':
                        await close_position(productType, position_symbol, 'short', SLEEP_TIME)
                    elif buy_sell_ratio_predict == "SELL" and candle_ta_result == "SELL" and position_side == 'long':
                        await close_position(productType, position_symbol, 'long', SLEEP_TIME)
                    else:
                        print_position(position_symbol, position_qty, position_pnl, position_side,
                                       position_liq_price)
                await asyncio.sleep(SLEEP_TIME)
        else:
            print("No current positions!")
            await asyncio.sleep(SLEEP_TIME)


async def close_position(productType, symbol, holdSide, sleep_time):
    position_close = flash_close_position(productType, symbol=symbol, holdSide=holdSide)
    if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
        print(f"Opened {holdSide} is successfully closed by algo!")
        bot_send_message(f"Opened {holdSide} is successfully closed by algo!")
    else:
        print(
            f"Error closing {holdSide} position for {symbol}: {position_close.status_code} {position_close.json()['msg']}")
        bot_send_message(
            f"Error closing {holdSide} position for {symbol}: {position_close.status_code} {position_close.json()['msg']}")
    await asyncio.sleep(sleep_time)


def print_position(symbol, qty, pnl, side, liq_price):
    print("Opened Position:\n"
          f"Symbol: {symbol}, QTY: {qty}, PNL: {pnl},\n"
          f"Side: {side}, Liq_price: {liq_price}")
    bot_send_message("Opened Position:\n"
                     f"Symbol: {symbol}, QTY: {qty}, PNL: {pnl},\n"
                     f"Side: {side}, Liq_price: {liq_price}")


# async def manage_position_close(productType, marginCoin, queue, public_queue):
#     """Отслеживание позиции
#        PNL текущей позиции
#        Отслеживание результата закрытой позиции"""
#
#     # For TradingView_TA
#     EXCHANGE = "BITGET"
#     INTERVAL = Interval.INTERVAL_1_MINUTE
#
#     # For candlestick_TA
#     GRANULARITY = '1m'
#     LIMIT = '4'
#
#     SLEEP_TIME = 10
#
#     #current_positions = get_all_positions(productType, marginCoin).json()['data']
#
#     opened_positions = []
#     closed_positions = []
#     while True:
#
#         if not queue.empty():
#             websocket_msg_private = await queue.get()
#             if websocket_msg_private['arg']['channel'] == 'positions':
#                 print(f"Received data POSITIONS: {websocket_msg_private}")
#
#             positions = await get_websocket_channel_data(websocket_msg_private, 'positions')
#             if positions and len(positions) > 0:
#                 # opened_positions = []
#                 # closed_positions = []
#                 for position in positions:
#                     if float(position['available']) > 0:
#                         opened_positions.append(position)
#                     elif float(position['available']) == 0:
#                         closed_positions.append(position)
#                         #if position in opened_positions:
#                             # delete position from opened_positions
#                 # print(f"\nOPENED_POS: {opened_positions}")
#                 # print(f"CLOSED_POS: {closed_positions}\n")
#
#             # Обработка открытых позиций
#             if len(opened_positions) > 0:
#                 for position in opened_positions:
#                     # if 'instId' in position:
#                     position_symbol = position['instId']
#                     # elif 'symbol' in position:
#                     #     position_symbol = position['symbol']
#                     position_side = position['holdSide']
#                     position_qty = position['total']
#                     position_pnl = round(float(position['unrealizedPL']), 2)
#                     # position_breakeven = float(position['breakEvenPrice'])
#                     position_liq_price = round(float(position['liquidationPrice']), 2)
#                     # position_marginsize = position['marginSize']
#                     # position_marginmode = position['marginMode']
#
#             if len(opened_positions) > 0 and len(closed_positions) == 0:
#                 if not public_queue.empty():
#                     websocket_msg_public = await public_queue.get()
#                     if websocket_msg_public['arg']['channel'] == 'ticker':
#                         print(f"Received data MARKET: {websocket_msg_public}")
#
#                     position_symbol_data = await get_websocket_channel_data(websocket_msg_public, 'ticker')
#
#                     if position_symbol_data and len(position_symbol_data) > 0:
#                         symbol_last_price = position_pnl + float(position_symbol_data[0]['lastPrice'])
#                     # if positions and len(positions) > 0:
#                     #     opened_positions = []
#                     #     #closed_positions = []
#                     #     for position in positions:
#                     #         #if float(position['available']) > 0:
#                     #         opened_positions.append(position)
#                     #         # elif float(position['available']) == 0:
#                     #         #     closed_positions.append(position)
#                     #
#                     #
#                     #     # Обработка открытых позиций
#                     #     if len(opened_positions) > 0:
#                     #
#                     #
#                     #         # if margin_mode == 'crossed':
#                     #         # elif margin_mode == 'isolated':
#                     #         #     pass
#                     #
#                     #         for position in opened_positions:
#                     #             # if 'instId' in position:
#                     #             position_symbol = position['instId']
#                     #             # elif 'symbol' in position:
#                     #             #     position_symbol = position['symbol']
#                     #             position_side = position['holdSide']
#                     #             position_qty = position['total']
#                     #             position_pnl = round(float(position['unrealizedPL']), 2)
#                     #             # position_breakeven = float(position['breakEvenPrice'])
#                     #             position_liq_price = round(float(position['liquidationPrice']), 2)
#                     #             # position_marginsize = position['marginSize']
#                     #             # position_marginmode = position['marginMode']
#
#                 # current_positions = get_all_positions(productType, marginCoin).json()['data']
#                 #
#                 # if current_positions:
#                 #     # if margin_mode == 'crossed':
#                 #     # elif margin_mode == 'isolated':
#                 #     #     pass
#                 #
#                 #     for position in current_positions:
#                 #         position_symbol = position['symbol']
#                 #         position_side = position['holdSide']
#                 #         position_qty = position['total']
#                 #         position_pnl = round(float(position['unrealizedPL']), 2)
#                 #         position_liq_price = round(float(position['liquidationPrice']), 2)
#                 #         # position_marginsize = position['marginSize']
#                 #         # position_marginmode = position['marginMode']
#
#                 ta_result = trade_tradingview_ta(position_symbol, EXCHANGE, INTERVAL)
#                 candle_ta_result = trade_candlestick_analysis(productType, position_symbol, GRANULARITY, LIMIT)
#                 buy_sell_ratio_predict = buy_sell_ratio_analysis(position_symbol)
#
#                 if ta_result and candle_ta_result:
#                     if "BUY" in ta_result and candle_ta_result == "BUY" and position_side == 'short':
#                         position_close = flash_close_position(productType, symbol=position_symbol, holdSide='short')
#                         if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
#                             print("Opened short is successfully closed by algo!")
#                             bot_send_message("Opened short is successfully closed by algo!")
#                             # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
#                             # pos_closed_qty = get_last_position(productType)['closeTotalPos']
#                             # print(f"Opened position short is successfully closed!\n"
#                             #       f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # bot_send_message(f"Opened position short is successfully closed!\n"
#                             #                  f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # print(position_close.json())
#                         else:
#                             print(position_close.status_code)
#                             print(position_close.json()['msg'])
#                             print(f"Opened position short isn't closed! Please, check account!\n"
#                                   f"Symbol: {position_symbol}")
#                             bot_send_message(f"Opened position short isn't successfully closed!\n"
#                                              f"Symbol: {position_symbol}")
#                         await asyncio.sleep(SLEEP_TIME)
#
#                     elif "SELL" in ta_result and candle_ta_result == "SELL" and position_side == 'long':
#                         position_close = flash_close_position(productType, symbol=position_symbol, holdSide='long')
#                         if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
#                             print("Opened long is successfully closed by algo!")
#                             bot_send_message("Opened long is successfully closed by algo!")
#                             # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
#                             # pos_closed_qty = get_last_position(productType)['closeTotalPos']
#                             # print(f"Opened position long is successfully closed!\n"
#                             #       f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # bot_send_message(f"Opened position long is successfully closed!\n"
#                             #                  f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # print(position_close.json())
#                         else:
#                             print(position_close.status_code)
#                             print(position_close.json()['msg'])
#                             print(f"Opened position long isn't closed! Please, check account!\n"
#                                   f"Symbol: {position_symbol}")
#                             bot_send_message(f"Opened position long isn't successfully closed!\n"
#                                              f"Symbol: {position_symbol}")
#                         await asyncio.sleep(SLEEP_TIME)
#
#                     else:
#                         print("Opened Position:\n"
#                               f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                               f"Side: {position_side}, Liq_price: {position_liq_price}")
#                         bot_send_message("Opened Position:\n"
#                                          f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                                          f"Side: {position_side}, Liq_price: {position_liq_price}")
#                         await asyncio.sleep(SLEEP_TIME)
#
#                 else:
#                     print(f"No tradingview_analysis for {position_symbol}!\n")
#                           # "Opened Position:\n"
#                           # f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                           # f"Side: {position_side}, Liq_price: {position_liq_price}")
#                     bot_send_message(f"No tradingview_analysis for {position_symbol}!\n")
#                                      # "Opened Position:\n"
#                                      # f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                                      # f"Side: {position_side}, Liq_price: {position_liq_price}")
#
#                     if buy_sell_ratio_predict == "BUY" and candle_ta_result == "BUY" and position_side == 'short':
#                         position_close = flash_close_position(productType, symbol=position_symbol, holdSide='short')
#                         if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
#                             print("Opened short is successfully closed by algo!")
#                             bot_send_message("Opened short is successfully closed by algo!")
#                             # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
#                             # pos_closed_qty = get_last_position(productType)['closeTotalPos']
#                             # print(f"Opened position short is successfully closed!\n"
#                             #       f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # bot_send_message(f"Opened position short is successfully closed!\n"
#                             #                  f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # print(position_close.json())
#                         else:
#                             print(position_close.status_code)
#                             print(position_close.json()['msg'])
#                             print(f"Opened position short isn't closed! Please, check account!\n"
#                                   f"Symbol: {position_symbol}")
#                             bot_send_message(f"Opened position short isn't successfully closed!\n"
#                                              f"Symbol: {position_symbol}")
#                         await asyncio.sleep(SLEEP_TIME)
#
#                     elif buy_sell_ratio_predict == "SELL" and candle_ta_result == "SELL" and position_side == 'long':
#                         position_close = flash_close_position(productType, symbol=position_symbol, holdSide='long')
#                         if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
#                             print("Opened long is successfully closed by algo!")
#                             bot_send_message("Opened long is successfully closed by algo!")
#                             # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
#                             # pos_closed_qty = get_last_position(productType)['closeTotalPos']
#                             # print(f"Opened position long is successfully closed!\n"
#                             #       f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # bot_send_message(f"Opened position long is successfully closed!\n"
#                             #                  f"Symbol: {position_symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
#                             # print(position_close.json())
#                         else:
#                             print(position_close.status_code)
#                             print(position_close.json()['msg'])
#                             print(f"Opened position long isn't closed! Please, check account!\n"
#                                   f"Symbol: {position_symbol}")
#                             bot_send_message(f"Opened position long isn't successfully closed!\n"
#                                              f"Symbol: {position_symbol}")
#                         await asyncio.sleep(SLEEP_TIME)
#
#                     else:
#                         print("Opened Position:\n"
#                               f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                               f"Side: {position_side}, Liq_price: {position_liq_price}")
#                         bot_send_message("Opened Position:\n"
#                                          f"Symbol: {position_symbol}, QTY: {position_qty}, PNL: {position_pnl},\n"
#                                          f"Side: {position_side}, Liq_price: {position_liq_price}")
#                     await asyncio.sleep(SLEEP_TIME)
#
#                 else:
#                     print("No current positions!")
#                     #bot_send_message("No current positions!")
#                     await asyncio.sleep(SLEEP_TIME)
#                 # else:
#                     #     print("Waiting for websocket_messages......")
#                     #     # bot_send_message("No current positions!")
#                     #     await asyncio.sleep(SLEEP_TIME)


async def manage_position(symbol, productType, marginCoin, result_predict):
    """Отслеживание условий открытия позиции
       Сигнал для открытия новых и закрытия текущих"""

    current_positions = get_all_positions(productType, marginCoin).json()['data']
    buy_sell_ratio_predict = buy_sell_ratio_analysis(symbol)
    funding_rate_percent = float(get_funding_rate(convert_usdt_symbol(symbol), "USDT-FUTURES").json()['data'][0]['fundingRate'])*100  #> 0.0050%


    if current_positions:
        #if margin_mode == 'crossed':
        # elif margin_mode == 'isolated':
        #     pass

        positions_long = []
        positions_short = []

        for position in current_positions:
            if position['holdSide'] == 'long':
                positions_long.append(position)
            elif position['holdSide'] == 'short':
                positions_short.append(position)
        if result_predict == "BUY" and buy_sell_ratio_predict == "BUY":# and funding_rate_percent < 0.0050:
            if len(positions_long) > 0 and len(positions_short) == 0:
                print("Long position is already opened!")
                bot_send_message("Long position is already opened!")
                for position in positions_long:
                    print(f"Symbol: {position['symbol']}, PNL: {round(float(position['unrealizedPL']), 2)}, "
                          f"Liq_price: {position['liquidationPrice']}")
                    bot_send_message(f"Symbol: {position['symbol']}, PNL: {round(float(position['unrealizedPL']), 2)}, "
                                     f"Liq_price: {position['liquidationPrice']}")
                return None

            elif len(positions_long) == 0 and len(positions_short) > 0:
                position_close = flash_close_position(productType, holdSide='short')
                if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
                    print("Opened short is successfully closed as new buy signal received!")
                    bot_send_message("Opened short is successfully closed as new buy signal received!")
                    # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
                    # pos_closed_qty = get_last_position(productType)['closeTotalPos']
                    # print(f"Opened position short is successfully closed!\n"
                    #       f"Symbol: {symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
                    # bot_send_message(f"Opened position short is successfully closed!\n"
                    #                  f"Symbol: {symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
                    # print(position_close.json())
                    return "open_buy"
                else:
                    print(position_close.status_code)
                    print(position_close.json()['msg'])
                    print(f"Opened position short isn't closed! Please, check account!\n"
                          f"Symbol: {symbol}")
                    bot_send_message(f"Opened position short isn't successfully closed!\n"
                                     f"Symbol: {symbol}")
                    return "open_buy"
            else:
                print("Exception is raised in manage_position 'BUY'!")
                bot_send_message("Exception is raised in manage_position 'BUY'!")
                return None

        elif result_predict == "SELL" and buy_sell_ratio_predict == "SELL":# and funding_rate_percent > 0.0100:
            if len(positions_short) > 0 and len(positions_long) == 0:
                print("Short position is already opened!")
                bot_send_message("Short position is already opened!")
                for position in positions_short:
                    print(f"Symbol: {position['symbol']}, PNL: {round(float(position['unrealizedPL']), 2)}, "
                          f"Liq_price: {position['liquidationPrice']}")
                    bot_send_message(f"Symbol: {position['symbol']}, PNL: {round(float(position['unrealizedPL']), 2)}, "
                                     f"Liq_price: {position['liquidationPrice']}")
                return None

            elif len(positions_short) == 0 and len(positions_long) > 0:
                position_close = flash_close_position(productType, holdSide='long')
                if position_close.status_code == 200 and position_close.json()['msg'] == 'success':
                    print("Opened long is successfully closed as new sell signal received!")
                    bot_send_message("Opened long is successfully closed as new sell signal received!")
                    # pos_net_profit = round(float(get_last_position_pnl(productType)), 2)
                    # pos_closed_qty = get_last_position(productType)['closeTotalPos']
                    # print(f"Opened position long is successfully closed!\n"
                    #       f"Symbol: {symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
                    # bot_send_message(f"Opened position long is successfully closed!\n"
                    #                  f"Symbol: {symbol}, QTY: {pos_closed_qty} PNL: {pos_net_profit}")
                    # print(position_close.json())
                    return "open_sell"
                else:
                    print(position_close.status_code)
                    print(position_close.json()['msg'])
                    print(f"Opened position long isn't closed! Please, check account!\n"
                          f"Symbol: {symbol}")
                    bot_send_message(f"Opened position long isn't successfully closed!\n"
                                     f"Symbol: {symbol}")
                    return "open_sell"
            else:
                print("Exception is raised in manage_position 'SELL'!")
                bot_send_message("Exception is raised in manage_position 'SELL'!")
                return None

        else:
            print("No proper conditions for open position!\n"
                  f"Result_predict: {result_predict}, Funding_rate: {round(float(funding_rate_percent), 6)} %, "
                  f"Buy_Sell: {buy_sell_ratio_predict}")
            bot_send_message("No proper conditions for open position!\n"
                             f"Result_predict: {result_predict}, Funding_rate: {round(float(funding_rate_percent), 6)} %, "
                             f"Buy_Sell: {buy_sell_ratio_predict}")
            return None
    else:
        if result_predict == 'BUY' and buy_sell_ratio_predict == "BUY":# and funding_rate_percent < 0.0050:
            return "open_buy"
        elif result_predict == 'SELL' and buy_sell_ratio_predict == "SELL":# and funding_rate_percent > 0.0100:
            return "open_sell"
        else:
            print("No proper conditions for open position!\n"
                  f"Result_predict: {result_predict}, Funding_rate: {round(float(funding_rate_percent), 6)} %, "
                  f"Buy_Sell: {buy_sell_ratio_predict}")
            bot_send_message("No proper conditions for open position!\n"
                             f"Result_predict: {result_predict}, Funding_rate: {round(float(funding_rate_percent), 6)} %, "
                             f"Buy_Sell: {buy_sell_ratio_predict}")
            return None

        # Make trade
        # def make_trade(SYMBOL, QTY, RESULT_PREDICT, PRODUCTTYPE, MARGINCOIN, MARGIN_MODE, SL='', TP=''):
        #     """Доработать открытие в hedge_mode с обязательной передачей параметра tradeSide в place_order!
        #        При открытии - выводить риск в % и деньгах
        #        Отслеживание позиции - при закрытии - PNL"""
        #     if SYMBOL and QTY and RESULT_PREDICT:
        #         if "BUY" in RESULT_PREDICT: # and manage_positions ==
        #             position_info = get_single_position(PRODUCTTYPE, SYMBOL, MARGINCOIN)
        #             print(position_info.status_code)
        #             print(position_info.json())
        #
        #             if not position_info.json()['data']:
        #                 position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "buy",
        #                                             marginMode=MARGIN_MODE, tp=TP, sl=SL)
        #                 if position_open.status_code == 200:
        #                     print(f"Новая позиция long {SYMBOL} успешно открыта!\n"
        #                           f"QTY: {QTY}")
        #                     bot_send_message(f"Новая позиция long {SYMBOL} успешно открыта!\n"
        #                                      f"QTY: {QTY}")
        #                     print(position_open.json())
        #
        #                 else:
        #                     print(position_open.status_code)
        #                     print(position_open.json()['msg'])
        #
        #             elif position_info.json()['data'][0]['holdSide'] == 'long':
        #                 print("Позиция long уже открыта!")
        #
        #             elif position_info.json()['data'][0]['holdSide'] == 'short':
        #
        #                 position_close = flash_close_position(PRODUCTTYPE, symbol=SYMBOL, holdSide='short')
        #                 if position_close.status_code == 200:
        #                     pos_net_profit = get_last_position_pnl(PRODUCTTYPE)
        #                     print(f"Открытая позиция short {SYMBOL} успешно закрыта!\n"
        #                           f"QTY: {QTY} PNL: {pos_net_profit}")
        #                     bot_send_message(f"Открытая позиция short {SYMBOL} успешно закрыта!\n"
        #                                      f"QTY: {QTY} PNL: {pos_net_profit}")
        #                     print(position_close.json())
        #                 else:
        #                     print(position_close.status_code)
        #                     print(position_close.json()['msg'])
        #
        #                 position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "buy",
        #                                             marginMode=MARGIN_MODE, tp=TP, sl=SL)
        #                 if position_open.status_code == 200:
        #                     print(f"Новая позиция long {SYMBOL} успешно открыта!\n"
        #                           f"QTY: {QTY}")
        #                     bot_send_message(f"Новая позиция long {SYMBOL} успешно открыта!\n"
        #                                      f"QTY: {QTY}")
        #                     print(position_open.json())
        #                 else:
        #                     print(position_open.status_code)
        #                     print(position_open.json()['msg'])
        #
        #         elif "SELL" in RESULT_PREDICT:
        #             position_info = get_single_position(PRODUCTTYPE, SYMBOL, MARGINCOIN)
        #             print(position_info.status_code)
        #             print(position_info.json())
        #
        #             if not position_info.json()['data']:
        #                 position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "sell",
        #                                             marginMode=MARGIN_MODE, tp=TP, sl=SL)
        #                 if position_open.status_code == 200:
        #                     print(f"Новая позиция short {SYMBOL} успешно открыта!\n"
        #                           f"QTY: {QTY}")
        #                     bot_send_message(f"Новая позиция short {SYMBOL} успешно открыта!\n"
        #                                      f"QTY: {QTY}")
        #                     print(position_open.json())
        #
        #                 else:
        #                     print(position_open.status_code)
        #                     print(position_open.json()['msg'])
        #
        #             elif position_info.json()['data'][0]['holdSide'] == 'short':
        #                 print("Позиция short уже открыта!")
        #
        #             elif position_info.json()['data'][0]['holdSide'] == 'long':
        #
        #                 position_close = flash_close_position(PRODUCTTYPE, symbol=SYMBOL, holdSide='short')
        #                 if position_close.status_code == 200:
        #                     pos_net_profit = get_last_position_pnl(PRODUCTTYPE)
        #                     print(f"Открытая позиция long {SYMBOL} успешно закрыта!\n"
        #                           f"QTY: {QTY} PNL: {pos_net_profit}")
        #                     bot_send_message(f"Открытая позиция long {SYMBOL} успешно закрыта!\n "
        #                                      f"QTY: {QTY} PNL: {pos_net_profit}")
        #                     print(position_close.json())
        #                 else:
        #                     print(position_close.status_code)
        #                     print(position_close.json()['msg'])
        #
        #                 position_open = place_order(SYMBOL, PRODUCTTYPE, MARGINCOIN, QTY, "sell",
        #                                             marginMode=MARGIN_MODE, tp=TP, sl=SL)
        #                 if position_open.status_code == 200:
        #                     print(f"Новая позиция short {SYMBOL} успешно открыта!\n"
        #                           f"QTY: {QTY}")
        #                     bot_send_message(f"Новая позиция short {SYMBOL} успешно открыта!\n"
        #                                      f"QTY: {QTY}")
        #                     print(position_open.json())
        #                 else:
        #                     print(position_open.status_code)
        #                     print(position_open.json()['msg'])
        #         else:
        #             print('Нет условий для открытия позиции!')
        #             return None
        #     else:
        #         print('Нет необходимых параметров для позиции:\n'
        #               f'SYMBOL: {SYMBOL}, QTY: {QTY}, SL: {SL}, TP: {TP}, RESULT_PREDICT: {RESULT_PREDICT}')
        #         return None









