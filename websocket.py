import asyncio
import base64
import hashlib
import hmac
from collections import deque

import websockets
import json
import time

#from utility import sign, pre_sign, get_timestamp
from config import API_KEY, API_SECRET, PASSPHRASE
from request_functions import get_server_time, get_all_positions
from telegram_bot import bot_send_message
from utility import clear_queue, convert_usdt_symbol

# Position channel
# Fill channel
# Account channel

URL_PUBLIC = 'wss://ws.bitget.com/v2/ws/public'
URL_PRIVATE = 'wss://ws.bitget.com/v2/ws/private'
METHOD_WEBSOCKET = 'GET'
REQUEST_PATH_WEBSOCKET = '/user/verify'


######################################################################
# Create Sign and Timestamp
######################################################################


# Creates TIMESTAMP
def get_server_timestamp():
    timestamp = int(get_server_time().json()['data']['serverTime'])
    return str(timestamp)


# Creates SIGN
def websocket_sign(pre_sign, secret_key):
    signature = hmac.new(secret_key.encode(), pre_sign.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


# Creates Message for sign
def pre_sign(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + str(body)


# # Parsing request parameters
# def parse_params_to_str(params):
#     params = [(key, val) for key, val in params.items()]
#     params.sort(key=lambda x: x[0])
#     url = '?' + toQueryWithNoEncode(params)
#     if url == '?':
#         return ''
#     return url
#
#
# # Converts Parameters to URL-string
# def toQueryWithNoEncode(params):
#     url = ''
#     for key, value in params:
#         url = url + str(key) + '=' + str(value) + '&'
#     return url[0:-1]


######################################################################
# For connection with Exchange Server
######################################################################

################################################################
# Subscribe to private
################################################################

# login to Websocket Private
async def websocket_private_authenticate(websocket):

    timestamp = get_server_timestamp()
    method = "GET"
    request_path = "/user/verify"
    body = ''
    signature = websocket_sign(pre_sign(timestamp, method, request_path, body), API_SECRET)

    auth_message = {
        "op": "login",
        "args": [
            {
                "apiKey": API_KEY,
                "passphrase": PASSPHRASE,
                "timestamp": timestamp,
                "sign": signature
            }

        ]
    }

    await websocket.send(json.dumps(auth_message))
    auth_response = await websocket.recv()
    print(f"Auth response: {auth_response}")


# Subscribe to channels
async def subscribe_to_private_data(websocket, productType, subscribe="subscribe"):

    subscribe_message = {
                "op": str.lower(subscribe),
                "args": [
                    # data is pushed, when open/close orders are created, filled, canceled
                    {
                        "instType": str.upper(productType),
                        "channel": "positions",
                        "instId": "default"
                    },
                    # data is pushed when the position totally closed
                    {
                        "instType": str.upper(productType),
                        "channel": "positions-history",
                        "instId": "default"
                    },
                    # # data is pushed, when transfer balance to futures, voucher deposit, orders are filled
                    # {
                    #     "instType": str.upper(productType),
                    #     "channel": "account",
                    #     "coin": "default"
                    # },
                    # # data will be pushed when order is filled
                    # {
                    #     "instType": str.upper(productType),
                    #     "channel": "fill",
                    #     "instId": "default"
                    # },
                    # # data will be pushed when orders are opened/closed, created, filled, canceled
                    # {
                    #     "instType": str.upper(productType),
                    #     "channel": "orders",
                    #     "instId": "default"
                    # },
                ]
            }
    await websocket.send(json.dumps(subscribe_message))
    subscribe_response = await websocket.recv()
    print(f"Subscription response: {subscribe_response}")


################################################################
# Processing data from Private channels
################################################################


# Instantly listen and Receive messages from websocket private channels
# Get info about positions actions
async def position_channel_messages(websocket_msg):
    if websocket_msg:
        if 'action' in websocket_msg and (websocket_msg['action'] == 'snapshot' or websocket_msg['action'] == 'update'):
            if websocket_msg['arg']['channel'] == 'positions':
                positions_list = websocket_msg['data']
                if positions_list:
                    print(f"Positions received!")
                else:
                    print("No positions found!")
                    positions_list = []
                return positions_list
            else:
                print(f"No data for Position_channel found!")
                return None
    else:
        print(f"No websocket_message for Position_channel found!")
        return None


# Get info about totally closed position
async def positions_history_last_closed(websocket_msg):

    if websocket_msg:
        if 'action' in websocket_msg and (websocket_msg['action'] == 'snapshot' or websocket_msg['action'] == 'update'):
            # print(websocket_msg)
            if websocket_msg['arg']['channel'] == 'positions-history':

                closed_position = websocket_msg['data'][0]
                if closed_position:
                    symbol = closed_position['instId']
                    qty = closed_position['closeSize']
                    marginmode = closed_position['marginMode']
                    holdside = closed_position['holdSide']
                    achievedprofits = float(closed_position['achievedProfits'])
                    settlefee = float(closed_position['settleFee'])
                    openfee = float(closed_position['openFee'])
                    closefee = float(closed_position['closeFee'])
                    pnl = achievedprofits + settlefee + openfee + closefee
                    print("Position is successfully closed!\n"
                          f"Symbol: {symbol}, Side: {holdside}, QTY: {qty}, PNL: {pnl}, Marg_m: {marginmode}")
                    bot_send_message("Position is successfully closed!\n"
                                     f"Symbol: {symbol}, Side: {holdside}, QTY: {qty}, PNL: {pnl}, Marg_m: {marginmode}")

            else:
                print(f"No data for Positions_history_channel found!")
                await asyncio.sleep(1)

    else:
        print(f"No websocket_message for Positions_history_channel found!")
        await asyncio.sleep(1)


# Get info about account changes
async def account_channel_messages(websocket):
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        if data['arg']['channel'] == 'account':
            account_list = data['data']
            if account_list:
                print(f"Account data received!")
                account = account_list[0]
                return account
            else:
                print("No account data found!")
                account = ''
                return account


# Get opened positions
async def get_websocket_channel_data(websocket_msg, channel_name):

    if websocket_msg:
        action = websocket_msg.get('action')
        channel = websocket_msg['arg'].get('channel')

        if action in ('snapshot', 'update'):
            if channel == str.lower(channel_name):
                channel_data = websocket_msg['data']
                return channel_data
    else:
        return None


# После успешной аутентификации можно отправлять торговые приказы и подписки
# Пример торгового приказа (замените на ваши параметры)
# order_message = {
#     "op": "order",
#     "args": {
#         "symbol": "BTCUSDT",
#         "side": "buy",
#         "type": "limit",
#         "price": "30000",
#         "quantity": "0.001",
#         "clientOid": "your_order_id"
#     }
# }
#
# await websocket.send(json.dumps(order_message))
# order_response = await websocket.recv()
# print(f"Order response: {order_response}")

################################################################
# Subscribe to public
################################################################

# Subscribe to channels
async def subscribe_to_public_data(websocket, productType, symbol, subscribe="subscribe"):
    #granularity = 'candle' + str.lower(granularity)
    subscribe_message = {
                "op": str.lower(subscribe),
                "args": [
                    # Retrieve the latest traded price, bid price, ask price and 24-hour trading volume of the instruments.
                    # When there is a change (deal, buy, sell, issue): 100ms to 300ms.
                    {
                        "instType": str.upper(productType),
                        "channel": "ticker",
                        "instId": str.upper(symbol)
                    }
                    # # Retrieve the candlesticks data of a symbol. Data will be pushed every 500 ms.
                    # # The channel will push a snapshot after successful subscribed, later on the updates will be pushed
                    # {
                    #     "instType": str.upper(productType),
                    #     "channel": str.lower(granularity),
                    #     "instId": str.upper(symbol)
                    # },

                ]
            }
    print(f"SUBSCR_MES: {subscribe_message}")
    await websocket.send(json.dumps(subscribe_message))

    subscribe_response = await websocket.recv()
    print(f"Subscription response: {subscribe_response}")

    # while True:
    #     response = await websocket.recv()
    #     print(f"Received: {response}")


# Instantly listen and Receive messages from websocket public channels
async def market_channel_messages(websocket):
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        if data['arg']['channel'] == 'ticker':
            market_data = data['data']
            if market_data:
                market_data = market_data[0]
                print(f"Market data received!")
                return market_data
            else:
                print("No market data found!")
                market_data = ""
                return market_data


async def candlestick_channel_messages(websocket, granularity):
    granularity = 'candle' + str.lower(granularity)
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        if data['arg']['channel'] == str.lower(granularity):
            candlestick_data = data['data']
            if candlestick_data:
                candlestick_data = candlestick_data[0]
                print(f"Candlestick data received!")
                return candlestick_data
            else:
                print("No candlestick data found!")
                candlestick_data = ""
                return candlestick_data


######################################################################
# Create Websocket connections
######################################################################

# async def websocket_public(productType, symbol, granularity):
#     async with websockets.connect(URL_PUBLIC) as websocket:
#         await subscribe_to_public_data(websocket, productType, symbol, granularity)
#         market = await market_channel_messages(websocket)
#         candlestick = await candlestick_channel_messages(websocket, granularity)
#     return market, candlestick


# async def get_message(websocket, queue, websocket_url='websocket_url'):
#     while True:
#         try:
#             message = await websocket.recv()
#             if message:
#                 if message == 'pong':
#                     print(f"Waiting for websocket data..... Connection to {websocket_url} keep alive!")
#                     await asyncio.sleep(1)
#                     continue
#                 else:
#                     try:
#                         data = json.loads(message)
#                         await queue.put(data)
#                         #await asyncio.sleep(1)
#                         return data
#                     except json.JSONDecodeError as e:
#                         print(f"Failed to decode JSON message: {message}")
#                         print(f"JSON decode error: {e}")
#             else:
#                 print("Received empty message from websocket!")
#                 continue
#
#         except websockets.ConnectionClosedError as e:
#             print(f"WebSocket connection closed with error: {e}")
#             return None
#         except Exception as e:
#             print(f"Error receiving message: {e}")
#             return None

async def get_message(websocket, queue, pos_check_queue, websocket_url='websocket_url', subscribed_symbols=None):
    while True:
        # try:
        message = await websocket.recv()
        if message:
            if message == 'pong':
                print(f"Waiting for websocket data..... Connection to {websocket_url} keep alive!")
                # await asyncio.sleep(1)
                #continue
                return message
                #break
            else:
                try:
                    data = json.loads(message)
                    if subscribed_symbols is None:
                        if await get_websocket_channel_data(data, 'positions'):
                            await pos_check_queue.put(data)
                        await queue.put(data)
                        return data

                    elif subscribed_symbols is not None:

                        if await get_websocket_channel_data(data, 'ticker'):
                            # print(f"Subcribed_Symbols in get_mes: {subscribed_symbols} ")
                            ticker_data = await get_websocket_channel_data(data, 'ticker')
                            symbol = ticker_data[0]['instId']
                            if symbol not in subscribed_symbols:
                                print(f"Read message for symbol {symbol}")
                                continue
                        if await get_websocket_channel_data(data, 'positions'):
                            await pos_check_queue.put(data)
                        await queue.put(data)
                        return data
                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON message: {message}")
                    print(f"JSON decode error: {e}")
        else:
            print("Received empty message from websocket!")
            # await asyncio.sleep(1)
            continue
            #return None

        # except websockets.ConnectionClosedError as e:
        #     print(f"WebSocket get_message connection closed with error: {e}")
        #     return None
        # except Exception as e:
        #     print(f"Error receiving message: {e}")
        #     return None


async def send_ping(websocket):
    while True:
        try:
            await websocket.send("ping")
            await asyncio.sleep(25)
        except websockets.ConnectionClosedError as e:
            print(f"WebSocket connection closed while sending ping: {e}")
            return
        except Exception as e:
            print(f"Error sending ping: {e}")
            return


# Get and process data from private channels
async def websocket_private_data(product_type, queue, pos_check_queue):
    while True:
        try:
            async with websockets.connect(URL_PRIVATE) as websocket:
                await websocket_private_authenticate(websocket)
                await subscribe_to_private_data(websocket, product_type)

                # ping_task = asyncio.create_task(send_ping(websocket))
                # message_task = asyncio.create_task(get_message(websocket, queue, websocket_url=URL_PRIVATE))
                #
                # await asyncio.gather(ping_task, message_task)

                ping_task = asyncio.create_task(send_ping(websocket))

                while True:
                    try:
                        websocket_msg = await get_message(websocket, queue, pos_check_queue, websocket_url=URL_PRIVATE)
                        if websocket_msg is not None:
                            # print(websocket_msg)
                            await positions_history_last_closed(websocket_msg)

                        # elif not (ping_task or websocket_msg):
                        #     break
                    except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
                        print(f"WebSocket_private get_message connection closed with error: {e}")
                        break
                    except Exception as e:
                        print(f"Error receiving message from WebSocket_private get_message: {e}")
                        break
        except websockets.ConnectionClosedError as e:
            print(f"WebSocket_private connection closed with error: {e}")
            await asyncio.sleep(5)  # Задержка перед повторным подключением
        except Exception as e:
            print(f"WebSocket_private task failed with error: {e}")
            await asyncio.sleep(5)  # Задержка перед повторным подключением


async def catch_subscr_msg(websocket, product_type, subscr_queue, public_queue):
    #while True:
    subscribed_symbols = set()
    if not subscr_queue.empty():
        symbols, subscribe = await subscr_queue.get()

        if symbols and subscribe:
            print(f"SYMBOLS: {symbols}, SUBSCR: {subscribe}")

            if subscribe == 'subscribe':
                for symbol in set(symbols):
                    #symbol = convert_usdt_symbol(symbol)
                    if symbol not in subscribed_symbols:
                        await subscribe_to_public_data(websocket, product_type, symbol, subscribe="subscribe")
                        subscribed_symbols.add(symbol)
                print(f"Subscribed to new symbols: {set(symbols)}")

            elif subscribe == 'unsubscribe':
                for symbol in set(symbols):
                    #symbol = convert_usdt_symbol(symbol)
                    if symbol in subscribed_symbols:
                        await subscribe_to_public_data(websocket, product_type, symbol, subscribe="unsubscribe")
                        subscribed_symbols.remove(symbol)
                print(f"Unsubscribed from symbols: {set(symbols)}")
                await clear_queue(public_queue)
            return subscribed_symbols
    else:
        print("Waiting for symbols and subscribe!")
        await asyncio.sleep(2)
        return subscribed_symbols

#
# async def websocket_receive_messages(websocket, messages_queue, stop_event):
#     while not stop_event.is_set():
#         try:
#             message = await websocket.recv()
#             await messages_queue.put(message)
#         except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
#             print(f"WebSocket receive connection closed with error: {e}")
#             stop_event.set()
#             break
#         except Exception as e:
#             print(f"Error receiving message from WebSocket: {e}")
#             stop_event.set()
#             break
#
# async def websocket_public_data(product_type, subscr_queue, public_queue, pos_check_queue):
#     while True:
#         try:
#             async with websockets.connect(URL_PUBLIC) as websocket:
#                 stop_event = asyncio.Event()
#                 messages_queue = asyncio.Queue()
#                 subscribed_symbols = None
#
#                 # Запуск задачи для отправки "ping"
#                 ping_task = asyncio.create_task(send_ping_public(websocket, stop_event))
#                 # Запуск задачи для получения сообщений
#                 receive_task = asyncio.create_task(websocket_receive_messages(websocket, messages_queue, stop_event))
#                 # Запуск задачи для периодической обработки сообщений
#                 processing_task = asyncio.create_task(process_messages_periodically(messages_queue, public_queue, pos_check_queue, subscribed_symbols, stop_event))
#
#                 while not stop_event.is_set():
#                     try:
#                         if not subscr_queue.empty():
#                             subscribed_symbols = await catch_subscr_msg(websocket, product_type, subscr_queue, public_queue)
#                             print(f"Subscribed to symbols: {subscribed_symbols}")  # Логирование подписанных символов
#
#                     except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
#                         print(f"WebSocket_public connection closed with error: {e}")
#                         stop_event.set()
#                         break
#                     except Exception as e:
#                         print(f"Error in main loop of WebSocket_public: {e}")
#                         stop_event.set()
#                         break
#
#                 stop_event.set()
#                 ping_task.cancel()
#                 receive_task.cancel()
#                 processing_task.cancel()
#                 try:
#                     await ping_task
#                 except asyncio.CancelledError:
#                     pass
#                 try:
#                     await receive_task
#                 except asyncio.CancelledError:
#                     pass
#                 try:
#                     await processing_task
#                 except asyncio.CancelledError:
#                     pass
#
#         except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
#             print(f"WebSocket_public connection closed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением
#         except Exception as e:
#             print(f"WebSocket_public task failed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением
#
# async def process_messages_periodically(messages_queue, public_queue, pos_check_queue, subscribed_symbols, stop_event):
#     while not stop_event.is_set():
#         await asyncio.sleep(2)
#         message = await messages_queue.get()
#         if message == 'pong':
#             print(f"Connection to WebSocket is alive")
#             continue
#
#         try:
#             data = json.loads(message)
#             if subscribed_symbols is None:
#                 if await get_websocket_channel_data(data, 'positions'):
#                     await pos_check_queue.put(data)
#                 await public_queue.put(data)
#             else:
#                 if await get_websocket_channel_data(data, 'ticker'):
#                     ticker_data = await get_websocket_channel_data(data, 'ticker')
#                     symbol = ticker_data[0]['instId']
#                     if symbol not in subscribed_symbols:
#                         continue
#                 if await get_websocket_channel_data(data, 'positions'):
#                     await pos_check_queue.put(data)
#                 await public_queue.put(data)
#         except json.JSONDecodeError as e:
#             print(f"Failed to decode JSON message: {message}")
#             print(f"JSON decode error: {e}")
#         except Exception as e:
#             print(f"Error processing message: {e}")
#
#
# async def send_ping_public(websocket, stop_event):
#     while not stop_event.is_set():
#         try:
#             await websocket.send('ping')
#             await asyncio.sleep(25)  # Отправлять ping каждые 25 секунд
#         except Exception as e:
#             print(f"Error sending ping: {e}")
#             stop_event.set()
#             break








########################################################################
# 1 way Websocket Public
########################################################################
# Send ping to Websocket_public to keep connection alive
async def send_ping_public(websocket, stop_event):
    while not stop_event.is_set():
        try:
            await websocket.send('ping')
            await asyncio.sleep(25)
        except websockets.ConnectionClosed:
            break


# Get and process data from public channels
async def process_messages_periodically(messages, buffer_queue):

    while True:
        await asyncio.sleep(10)  # Укажите нужный интервал времени

        if messages:
            # Копировать и очистить список сообщений для новой порции
            messages_to_process = messages.copy()
            messages.clear()
            # Добавить сообщения в очередь в реверсивном порядке
            for message in reversed(messages_to_process):
                await buffer_queue.put(message)


async def websocket_public_data(product_type, subscr_queue, public_queue, pos_check_queue):
    while True:
        try:
            async with websockets.connect(URL_PUBLIC) as websocket:
                stop_event = asyncio.Event()
                buffer_queue = asyncio.Queue()
                subscribed_symbols = None
                messages = [] #deque(maxlen=1)  # []

                # Запуск задачи для отправки "ping"
                ping_task = asyncio.create_task(send_ping_public(websocket, stop_event))
                # Запуск задачи для периодической обработки сообщений
                processing_task = asyncio.create_task(process_messages_periodically(messages, buffer_queue))

                while True:
                    try:
                        if not subscr_queue.empty():
                            subscribed_symbols = await catch_subscr_msg(websocket, product_type, subscr_queue, public_queue)
                            print(f"Subscribed to symbols: {subscribed_symbols}")  # Логирование подписанных символов

                        message = await websocket.recv()
                        # Логирование всех полученных сообщений
                        # print(f"Received message: {message}")
                        messages.append(message)

                        while not buffer_queue.empty():
                            message = await buffer_queue.get()
                            if message == 'pong':
                                print(f"Connection to WebSocket is alive")
                                await clear_queue(buffer_queue)
                                continue

                            try:
                                data = json.loads(message)
                                # Логирование данных перед фильтрацией
                                # print(f"Processing message: {data}")
                                if subscribed_symbols is None:
                                    if await get_websocket_channel_data(data, 'positions'):
                                        await pos_check_queue.put(data)
                                    await public_queue.put(data)
                                else:
                                    if await get_websocket_channel_data(data, 'ticker'):
                                        ticker_data = await get_websocket_channel_data(data, 'ticker')
                                        symbol = ticker_data[0]['instId']
                                        if symbol not in subscribed_symbols:
                                            continue
                                    if await get_websocket_channel_data(data, 'positions'):
                                        await pos_check_queue.put(data)
                                    await public_queue.put(data)
                                await clear_queue(buffer_queue)
                            except json.JSONDecodeError as e:
                                print(f"Failed to decode JSON message: {message}")
                                print(f"JSON decode error: {e}")

                    except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
                        print(f"WebSocket_public connection closed with error: {e}")
                        break
                    except Exception as e:
                        print(f"Error receiving message from WebSocket_public get_message: {e}")
                        break

                stop_event.set()
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass

                processing_task.cancel()
                try:
                    await processing_task
                except asyncio.CancelledError:
                    pass

        except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
            print(f"WebSocket_public connection closed with error: {e}")
            await asyncio.sleep(5)  # Задержка перед повторным подключением
        except Exception as e:
            print(f"WebSocket_public task failed with error: {e}")
            await asyncio.sleep(5)  # Задержка перед повторным подключением

########################################################################





# async def websocket_public_data(product_type, subscr_queue, public_queue, pos_check_queue):
#     while True:
#         try:
#             async with websockets.connect(URL_PUBLIC) as websocket:
#                 stop_event = asyncio.Event()
#                 buffer_queue = asyncio.Queue()
#                 subscribed_symbols = None
#
#                 # Запуск задачи для отправки "ping"
#                 ping_task = asyncio.create_task(send_ping_public(websocket, stop_event))
#
#                 while True:
#                     try:
#                         if not subscr_queue.empty():
#                             subscribed_symbols = await catch_subscr_msg(websocket, product_type, subscr_queue, public_queue)
#                             print(f"Subscribed to symbols: {subscribed_symbols}")  # Логирование подписанных символов
#
#                         message = await websocket.recv()
#                         #print(f"Received message: {message}")  # Логирование всех полученных сообщений
#                         await buffer_queue.put(message)
#
#                         while not buffer_queue.empty():
#                             message = await buffer_queue.get()
#                             if message == 'pong':
#                                 print(f"Connection to WebSocket is alive")
#                                 continue
#
#                             try:
#                                 data = json.loads(message)
#                                 #print(f"Processing message: {data}")  # Логирование данных перед фильтрацией
#                                 if subscribed_symbols is None:
#                                     if await get_websocket_channel_data(data, 'positions'):
#                                         await pos_check_queue.put(data)
#                                     await public_queue.put(data)
#                                 else:
#                                     if await get_websocket_channel_data(data, 'ticker'):
#                                         ticker_data = await get_websocket_channel_data(data, 'ticker')
#                                         symbol = ticker_data[0]['instId']
#                                         if symbol not in subscribed_symbols:
#                                             continue
#                                     if await get_websocket_channel_data(data, 'positions'):
#                                         await pos_check_queue.put(data)
#                                     await public_queue.put(data)
#                             except json.JSONDecodeError as e:
#                                 print(f"Failed to decode JSON message: {message}")
#                                 print(f"JSON decode error: {e}")
#
#                     except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
#                         print(f"WebSocket_public connection closed with error: {e}")
#                         break
#                     except Exception as e:
#                         print(f"Error receiving message from WebSocket_public get_message: {e}")
#                         break
#
#                 stop_event.set()
#                 ping_task.cancel()
#                 try:
#                     await ping_task
#                 except asyncio.CancelledError:
#                     pass
#
#         except (websockets.ConnectionClosed, websockets.ConnectionClosedError) as e:
#             print(f"WebSocket_public connection closed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением
#         except Exception as e:
#             print(f"WebSocket_public task failed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением


# Gives signal and defines symbols to subscribe or unsubscribe
async def manage_websocket_public_subscriptions(subscr_queue, pos_check_queue):

    while True:
        if not pos_check_queue.empty():
            websocket_msg = await pos_check_queue.get()
            print(f"WEBSOCKET_MSG: {websocket_msg}")

            positions = await get_websocket_channel_data(websocket_msg, 'positions')
            if positions and len(positions) > 0:
                opened_positions = []
                closed_positions = []
                for position in positions:
                    if float(position['available']) > 0:
                        opened_positions.append(position)
                    elif float(position['available']) == 0:
                        closed_positions.append(position)
                print(f"\nOPENED_POS: {opened_positions}")
                print(f"CLOSED_POS: {closed_positions}\n")

                # Обработка открытых позиций
                if len(opened_positions) > 0:
                    symbols = [position['instId'] for position in opened_positions]
                    subscribe = 'subscribe'
                    await asyncio.sleep(1)
                    await subscr_queue.put((symbols, subscribe))
                    print(f"Subscribed to new symbols: {set(symbols)}")


                # Обработка закрытых позиций
                elif len(closed_positions) > 0:
                    symbols = [position['instId'] for position in closed_positions]
                    subscribe = 'unsubscribe'
                    await asyncio.sleep(1)
                    await subscr_queue.put((symbols, subscribe))
                    print(f"Unsubscribed from symbols: {set(symbols)}")

            else:
                print("Waiting for opened or closed positions.....")
                await asyncio.sleep(2)
                continue
        else:
            print("Waiting for queue_message.....")
            await asyncio.sleep(2)
            #continue




# async def manage_websocket_public_subscriptions(websocket, product_type, queue):
#     subscribed_symbols = set()
#
#     # Подписка на текущие открытые позиции при старте
#     # current_positions = get_all_positions(product_type, margin_coin).json()['data']
#     # if current_positions:
#     #     symbols = [position['symbol'] for position in current_positions]
#     #     for symbol in set(symbols):
#     #         await subscribe_to_public_data(websocket, product_type, symbol, subscribe='subscribe')
#     #         subscribed_symbols.add(symbol)
#     #     print(f"Subscribed to initial symbols: {subscribed_symbols}")
#     #     await asyncio.sleep(5)
#     #     return
#     while True:
#
#         websocket_msg = await queue.get()
#         opened_positions = await get_websocket_channel_data(websocket_msg, 'positions')
#         print(f"\nOPENED_POS: {opened_positions}")
#         closed_positions = await get_websocket_channel_data(websocket_msg, 'positions-history')
#         print(f"CLOSED_POS: {closed_positions}\n")
#
#         # Обработка открытых позиций
#         if opened_positions:
#             symbols = [position['instId'] for position in opened_positions]
#             for symbol in set(symbols):
#                 if symbol not in subscribed_symbols:
#                     await subscribe_to_public_data(websocket, product_type, symbol, subscribe='subscribe')
#                     subscribed_symbols.add(symbol)
#             print(f"Subscribed to new symbols: {set(symbols)}")
#             #break
#
#         # Обработка закрытых позиций
#         elif closed_positions and not opened_positions:
#             symbols = [position['instId'] for position in closed_positions]
#             for symbol in set(symbols):
#                 if symbol in subscribed_symbols:
#                     await subscribe_to_public_data(websocket, product_type, symbol, subscribe='unsubscribe')
#                     subscribed_symbols.remove(symbol)
#             print(f"Unsubscribed from symbols: {set(symbols)}")
#             #break
#
#         else:
#             print("Waiting for subscription.....")
#             await asyncio.sleep(2)
#
#             #break




# async def manage_websocket_public_subscriptions(product_type, margin_coin, queue):
#     async with websockets.connect(URL_PUBLIC) as websocket:
#         current_positions = get_all_positions(product_type, margin_coin).json()['data']
#         if current_positions:
#             symbols = [position['symbol'] for position in current_positions]
#             await websocket_public_data(websocket, product_type, symbols, 'subscribe', queue)
#             print("Subscribed to websocket_public_data successfully!\n"
#                   f"Symbols: {symbols}")
#
#         while True:
#             if not queue.empty():
#                 websocket_msg = await queue.get()
#                 if websocket_msg:
#                     action = websocket_msg.get('action')
#                     channel = websocket_msg['arg'].get('channel')
#
#                     if action in ('snapshot', 'update'):
#                         if channel == 'positions':
#                             opened_positions = websocket_msg['data']
#                             if opened_positions:
#                                 symbols = [position['instId'] for position in opened_positions]
#                                 await websocket_public_data(websocket, product_type, symbols, 'subscribe', queue)
#                                 print("Subscribed to websocket_public_data successfully!\n"
#                                       f"Symbols: {symbols}")
#
#                         elif channel == 'positions-history':
#                             closed_positions = websocket_msg['data']
#                             if closed_positions:
#                                 symbols = [position['instId'] for position in closed_positions]
#                                 await websocket_public_data(websocket, product_type, symbols, 'unsubscribe', queue)
#                                 print("Unsubscribed from websocket_public_data successfully!\n"
#                                       f"Symbols: {symbols}")
#
#             else:
#                 print("Waiting for public_subscriptions.....")
#                 await asyncio.sleep(2)





########################################
# Different kinds of Websocket Function
########################################

# async def websocket_private(productType):
#     async with websockets.connect(URL_PRIVATE) as websocket:
#         await websocket_private_authenticate(websocket)
#         await subscribe_to_private_data(websocket, productType)
#         position = await position_channel_messages(websocket)
#         position_history = await position_history_channel_messages(websocket)
#         account = await account_channel_messages(websocket)
#     return position, position_history, account


# async def websocket_private(product_type, queue):
#     async with websockets.connect(URL_PRIVATE) as websocket:
#         await websocket_private_authenticate(websocket)
#         # Пример подписки на рыночные данные
#         await subscribe_to_private_data(websocket, product_type)
#         while True:
#             message = await websocket.recv()
#             data = json.loads(message)
#             # Добавьте полученные данные в очередь
#             await queue.put(data)

# async def receive_messages(websocket, queue):
#     while True:
#         try:
#             message = await websocket.recv()
#             if message:
#                 if message == 'pong':
#                     continue
#                 else:
#                     try:
#                         data = json.loads(message)
#                         await queue.put(data)
#                     except json.JSONDecodeError as e:
#                         print(f"Failed to decode JSON message: {message}")
#                         print(f"JSON decode error: {e}")
#             else:
#                 print("Received empty message")
#         except websockets.ConnectionClosedError as e:
#             print(f"WebSocket connection closed with error: {e}")
#             break
#         except Exception as e:
#             print(f"Error receiving message: {e}")
#             break
#
#
# async def websocket_private(product_type, queue):
#
#     while True:
#         try:
#             async with websockets.connect(URL_PRIVATE) as websocket:
#                 await websocket_private_authenticate(websocket)
#                 await subscribe_to_private_data(websocket, product_type)
#
#                 # Запускаем фоновую задачу для получения сообщений
#                 receive_task = asyncio.create_task(receive_messages(websocket, queue))
#
#
#                 # Периодически отправляем heartbeat, чтобы не отключаться
#                 while True:
#                     await websocket.send("ping")#('{"op": "ping"}')
#                     await asyncio.sleep(25)  # Отправляем пинг каждые 25 секунд
#
#         except websockets.ConnectionClosedError as e:
#             print(f"WebSocket connection closed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением
#         except Exception as e:
#             print(f"WebSocket task failed with error: {e}")
#             await asyncio.sleep(5)  # Задержка перед повторным подключением


#########################################
# Processing data from Private channels
#########################################
# # Check subscriptions
# async def check_subscription(queue, channel):
#     while True:
#         if not queue.empty():
#             data = await queue.get()
#             if 'event' in data and data['event'] == 'subscribe' and data['arg']['channel'] == str.lower(channel):
#                 print(f"Successfully subscribed!\n"
#                       f"productType: {data['arg']['instType']}, channel: {data['arg']['channel']}")
#                 return
#             else:
#                 print(f"No subscription for channel: {channel} found!")
#                 return None
#         else:
#             print("No websocket_messages found!")
#             return None
#
#
# # Instantly listen and Receive messages from websocket private channels
# # Get info about positions actions
# async def position_channel_messages(queue):
#     channel = 'positions'
#     check_channel_subscription = await check_subscription(queue, channel)
#     if check_channel_subscription:
#
#         while True:
#
#             data = await queue.get()
#             if 'action' in data and data['action'] == 'snapshot' and data['arg']['channel'] == 'positions':
#                 positions_list = data['data']
#                 if positions_list:
#                     print(f"Positions received!")
#                 else:
#                     print("No positions found!")
#                     positions_list = []
#                 return positions_list
#             else:
#                 print(f"No data for channel: {channel} found!")
#                 return None
#     else:
#         print(f"No subscription for channel: {channel} found!")
#         return None
#
#
# # Get info about totally closed position
# async def position_history_channel_messages(queue):
#     # channel = 'positions-history'
#     # check_channel_subscription = await check_subscription(queue, channel)
#     # if check_channel_subscription:
#
#     while True:
#         if not queue.empty():
#             data = await queue.get()
#             if 'action' in data and data['action'] == 'snapshot' and data['arg']['channel'] == 'positions-history':
#                 position_closed = data['data'][0]
#                 if position_closed:
#                     print(f"Position totally closed received!")
#                     return position_closed
#
#                 else:
#                     print("No positions totally closed found!")
#                     await asyncio.sleep(2)
#                     continue
#         else:
#             print("No positions totally closed found!")
#             await asyncio.sleep(2)
#             continue
#
#     # else:
#     #     print(f"No subscription for channel: {channel} found!")
#     #     return


# # Get info about account changes
# async def account_channel_messages(websocket):
#     while True:
#         message = await websocket.recv()
#         data = json.loads(message)
#         if data['arg']['channel'] == 'account':
#             account_list = data['data']
#             if account_list:
#                 print(f"Account data received!")
#                 account = account_list[0]
#                 return account
#             else:
#                 print("No account data found!")
#                 account = ''
#                 return account


# После успешной аутентификации можно отправлять торговые приказы и подписки
# Пример торгового приказа (замените на ваши параметры)
# order_message = {
#     "op": "order",
#     "args": {
#         "symbol": "BTCUSDT",
#         "side": "buy",
#         "type": "limit",
#         "price": "30000",
#         "quantity": "0.001",
#         "clientOid": "your_order_id"
#     }
# }
#
# await websocket.send(json.dumps(order_message))
# order_response = await websocket.recv()
# print(f"Order response: {order_response}


########################################
# Processing data from Public channels
########################################
# # Instantly listen and Receive messages from websocket public channels
# async def market_channel_messages(websocket):
#     while True:
#         message = await websocket.recv()
#         data = json.loads(message)
#         if data['arg']['channel'] == 'ticker':
#             market_data = data['data']
#             if market_data:
#                 market_data = market_data[0]
#                 print(f"Market data received!")
#                 return market_data
#             else:
#                 print("No market data found!")
#                 market_data = ""
#                 return market_data
#
#
# async def candlestick_channel_messages(websocket, granularity):
#     granularity = 'candle' + str.lower(granularity)
#     while True:
#         message = await websocket.recv()
#         data = json.loads(message)
#         if data['arg']['channel'] == str.lower(granularity):
#             candlestick_data = data['data']
#             if candlestick_data:
#                 candlestick_data = candlestick_data[0]
#                 print(f"Candlestick data received!")
#                 return candlestick_data
#             else:
#                 print("No candlestick data found!")
#                 candlestick_data = ""
#                 return candlestick_data


