import asyncio

from tradingview_ta import Interval
from account import *
from money_management import sl_tp_count, lot_count, trade_equity_count
from strategies import tradingviewTA_candleSpike
from trades import make_trade, manage_position, manage_position_close
import time

from websocket import websocket_private_data, manage_websocket_public_subscriptions, websocket_public_data


async def main():
    private_queue = asyncio.Queue()
    pos_check_queue = asyncio.Queue()
    subscr_queue = asyncio.Queue()
    public_queue = asyncio.Queue()
    #positions_queue = asyncio.Queue()

    async def websocket_task():
        while True:
            try:
                # private_task = asyncio.create_task(websocket_private_data(PRODUCTTYPE, private_queue))
                # public_task = asyncio.create_task(websocket_public_data(PRODUCTTYPE, MARGINCOIN, private_queue))
                # await asyncio.gather(private_task, public_task)

                await asyncio.gather(
                    manage_websocket_public_subscriptions(subscr_queue, pos_check_queue),
                    websocket_private_data(PRODUCTTYPE, private_queue, pos_check_queue),  #websocket_private(PRODUCTTYPE, private_queue)
                    websocket_public_data(PRODUCTTYPE, subscr_queue, public_queue, pos_check_queue)
                )

            except Exception as e:
                print(f"WebSocket task failed with error: {e}")
                await asyncio.sleep(5)  # Задержка перед перезапуском задачи

    async def manage_position_close_task():

        # Manage positions close
        await manage_position_close(PRODUCTTYPE, private_queue, public_queue)

    async def trading_task():
        while True:
            try:

                # Get Symbol and Analyze symbol, get predict
                SYMBOL, RESULT_PREDICT = await tradingviewTA_candleSpike(EXCHANGE, INTERVAL, PRODUCTTYPE,
                                                                         GRANULARITY, LIMIT, VOLUME, SYMB_DEF)

                # Manage positions
                manage_positions = await manage_position(SYMBOL, PRODUCTTYPE, MARGINCOIN, RESULT_PREDICT)
                if not manage_positions:
                    await asyncio.sleep(60)#time.sleep(60)
                    continue


                # Get Market and candlestick data
                #market, candlestick = await websocket_public(PRODUCTTYPE, SYMBOL, GRANULARITY)

                # Set Position mode for Account
                set_position_mode_for_account(PRODUCTTYPE, SYMBOL, MARGINCOIN, POSITION_MODE)

                # Set Margin mode for Account
                new_margin_mode = set_margin_mode_for_account(PRODUCTTYPE, SYMBOL, MARGINCOIN, MARGIN_MODE)

                # Set Leverage
                new_leverage = set_leverage_for_symbol(PRODUCTTYPE, SYMBOL, MARGINCOIN, LEVERAGE, new_margin_mode)

                # Calculate stop-loss and take-profit levels
                SL, TP, DELTA_SL = sl_tp_count(RR, SYMBOL, PRODUCTTYPE, GRANULARITY, LIMIT, RESULT_PREDICT)


                # Calculate trade equity for position (% of account in USDT according to TRADE_RISK)
                trade_equity = trade_equity_count(SYMBOL, PRODUCTTYPE, MARGINCOIN, TRADE_RISK)

                # Calculate position quantity
                QTY = lot_count(SYMBOL, PRODUCTTYPE, SL, DELTA_SL, trade_equity, TRADE_RISK, new_leverage, PFF)
                # except (KeyError, ValueError, TypeError) as e:
                #     print(f"Error processing symbol {SYMBOL}: {e}")

                # Make trade
                new_trade = make_trade(SYMBOL, QTY, PRODUCTTYPE, MARGINCOIN, new_margin_mode, manage_positions, SL=SL, TP=TP)

                # Adjust additional margin (trade_equity) to the opened position in isolated mode
                if new_margin_mode == 'isolated':
                    change_position_margin(SYMBOL, PRODUCTTYPE, MARGINCOIN, new_trade, new_margin_mode, RESULT_PREDICT, trade_equity)

                await asyncio.sleep(10)#time.sleep(10)
            except Exception as e:
                print(f"Trading task failed with error: {e}")
                await asyncio.sleep(5)  # Задержка перед перезапуском задачи


    # websocket_task = asyncio.create_task(websocket_task())
    # trading_task = asyncio.create_task(trading_task())
    # manage_position_close_task = asyncio.create_task(manage_position_close_task())
    #
    # await asyncio.gather(manage_position_close_task, trading_task, websocket_task)  # position_message_task()
    #Запуск обеих задач параллельно
    await asyncio.gather(manage_position_close_task(), trading_task(), websocket_task())  # position_message_task()



# Вывод результата
if __name__ == '__main__':
    # General
    #SYMBOL = "SETHSUSDT"
    PRODUCTTYPE = "SUSDT-FUTURES"               # account type
    MARGINCOIN = "SUSDT"                        # currency of the margin
    VOLUME = 1000000                           # trading volume in quote currency (USDT) of the symbol
    SYMB_DEF = [('SBTCSUSDT', '1'),             # default list of symbols if problems with get_max_traded_symbols
                ('SETHSUSDT', '2'),
                ('SXRPSUSDT', '3')]

    # Account
    MARGIN_MODE = 'crossed'                     # crossed or isolated
    LEVERAGE = 10                               # depends on SYMBOL (from 10x to 125x), default (10x)

    # Position
    POSITION_MODE = 'one_way_mode'              # one_way_mode: one-way mode,  hedge_mode: hedge mode for all symbols
    PFF = 0.05                                  # price fluctuation factor - for counting the initial_margin for position

    # for tradinview_TA
    EXCHANGE = "BITGET"                         # name of exchange for tradingview analysis
    INTERVAL = Interval.INTERVAL_5_MINUTES  #INTERVAL_1_MINUTE       # interval for prediction in tradingview

    # for candlestick analysis
    GRANULARITY = '5m'                          # interval of each candle
    CANDLESTICK_DATA = 'candle5m'               # interval of each candle for websocket
    LIMIT = '4'                                 # quantity of last candles analyzed (including current)

    # for sl, tp, lot count
    TRADE_RISK = 0.03                           # risk per trade
    RR = 1.5                                      # risk/reward per trade

    asyncio.run(main())



    # result = output.get_analysis().summary
    # print(result)

    # Тест функций
    #response = place_order_futures_market("sbtcsusdt", 0.01, "buy")
    #response = flash_close_position_futures()
    #response = get_all_account_info()
    #response = get_account_info('susdt-futures')
    #response = get_all_positions_info_futures()
    #response = get_pending_orders_info_futures()
    # response = get_single_position_info_futures("sethsusdt")
    # if response.json()['data'] == []:
    #     print("None")
    # else:
    #     print(response.status_code)
    #     print(response.json())

# params_dict = {"symbol": "TRXUSDT", "marginCoin": "USDT"}
# request_path = request_path + parse_params_to_str(params_dict)
# body = {"productType":"usdt-futures",
#         "symbol":"BTCUSDT",
#         "size":"8",
#         "marginMode":"crossed",
#         "side":"buy",
#         "orderType":"limit",
#         "clientOid":"channel#123456"
#         }
