import base64
import hmac
import time
import requests
import json
import random
from urllib.parse import urlencode

from config import API_KEY, API_SECRET, PASSPHRASE

######################################################################
# Create Sign
######################################################################


# Creates ACCESS-TIMESTAMP
def get_timestamp():
    return str(int(time.time() * 1000))


# Creates ACCESS-SIGN
def sign(pre_sign, secret_key):
    signature = hmac.new(secret_key.encode('UTF-8'), pre_sign.encode('UTF-8'), digestmod='sha256').digest()
    return base64.b64encode(signature)


# Creates Message for sign
def pre_sign(timestamp, method, request_path, body):
    return str(timestamp) + str.upper(method) + request_path + str(body)


# Parsing request parameters
def parse_params_to_str(params):
    params = [(key, val) for key, val in params.items()]
    params.sort(key=lambda x: x[0])
    url = '?' + toQueryWithNoEncode(params)
    if url == '?':
        return ''
    return url


# Converts Parameters to URL-string
def toQueryWithNoEncode(params):
    url = ''
    for key, value in params:
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]


######################################################################
# For connection with Exchange Server
######################################################################


# Makes POST-request
def make_request_post(access_key, access_sign, passphrase, timestamp, request_path, body):
    api_url = "https://api.bitget.com"

    headers = {
        "ACCESS-KEY": access_key,
        "ACCESS-SIGN": access_sign,
        "ACCESS-PASSPHRASE": passphrase,
        "ACCESS-TIMESTAMP": timestamp,
        "locale": "en-US",
        "Content-Type": "application/json"
    }
    url = f'{api_url}{request_path}'

    max_retries = 5
    retries = 0
    time_sleep = 60

    while retries < max_retries:
        try:
            response = requests.post(url=url, data=body, headers=headers)
            response.raise_for_status()
            try:
                # Проверка декодирования JSON без использования результата
                _ = response.json()
            except requests.exceptions.JSONDecodeError:
                print("Ошибка декодирования JSON. Возможно, сервер вернул пустой или некорректный ответ.")
                print(f"Ответ сервера: {response.text}")
                retries += 1
                time.sleep(time_sleep)
                continue  # Повторить запрос

            return response

        except ConnectionError as e:
            print(f"Can't connect to server! Error: {e}.\n"
                  f"Retrying ({retries + 1}/{max_retries})...")
            retries += 1
            time.sleep(time_sleep)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break  # Exit the loop on other types of request errors

    print("Max retries exceeded. Exiting.")
    return None


# Makes GET-request
def make_request_get(access_key, access_sign, passphrase, timestamp, request_path, body):
    api_url = "https://api.bitget.com"

    headers = {
        "ACCESS-KEY": access_key,
        "ACCESS-SIGN": access_sign,
        "ACCESS-PASSPHRASE": passphrase,
        "ACCESS-TIMESTAMP": timestamp,
        "locale": "en-US",
        "Content-Type": "application/json"
    }
    url = f'{api_url}{request_path}'

    max_retries = 5
    retries = 0
    time_sleep = 60

    while retries < max_retries:
        try:
            response = requests.get(url=url, data=body, headers=headers)
            response.raise_for_status()  # Проверяем успешность запроса

            try:
                # Проверка декодирования JSON без использования результата
                _ = response.json()
            except requests.exceptions.JSONDecodeError:
                print("Ошибка декодирования JSON. Возможно, сервер вернул пустой или некорректный ответ.")
                print(f"Ответ сервера: {response.text}")
                retries += 1
                time.sleep(time_sleep)
                continue  # Повторить запрос

            return response  # Возвращаем response, если декодирование успешно

        except ConnectionError as e:
            print(f"Can't connect to server! Error: {e}.\n"
                  f"Retrying ({retries + 1}/{max_retries})...")
            retries += 1
            time.sleep(time_sleep)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            break  # Exit the loop on other types of request errors

    print("Max retries exceeded. Exiting.")
    return None



# Makes GET-request
# def make_request_get(access_key, access_sign, passphrase, timestamp, request_path, body):
#     api_url = "https://api.bitget.com"
#
#     headers = {
#         "ACCESS-KEY": access_key,
#         "ACCESS-SIGN": access_sign,
#         "ACCESS-PASSPHRASE": passphrase,
#         "ACCESS-TIMESTAMP": timestamp,
#         "locale": "en-US",
#         "Content-Type": "application/json"
#     }
#     url = f'{api_url}{request_path}'
#
#     max_retries = 5
#     retries = 0
#
#     while retries < max_retries:
#         try:
#             response = requests.get(url=url, data=body, headers=headers)
#             return response
#         except ConnectionError as e:
#             print(f"Can't connect to server! Error: {e}.\n"
#                   f"Retrying ({retries + 1}/{max_retries})...")
#             retries += 1
#             time.sleep(2)
#         except requests.exceptions.RequestException as e:
#             print(f"An error occurred: {e}")
#             break  # Exit the loop on other types of request errors
#
#     print("Max retries exceeded. Exiting.")
#     return None


##############################################
#Действия со счетами и ордерами
##############################################
def set_position_mode(productType, posMode):
    params = dict()
    params["productType"] = str.upper(productType)     # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["posMode"] = str(posMode)                   # one_way_mode or hedge_mode

    # POST
    method = "POST"
    timestamp = get_timestamp()                     # get_timestamp()
    request_path = "/api/v2/mix/account/set-position-mode"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def adjust_position_margin(symbol, productType, marginCoin, holdSide, amount):
    """Function is used for isolated margin mode in position"""
    params = dict()
    params["symbol"] = str.upper(symbol)            # trading pair, for example "SETHSUSDT"
    params["productType"] = str.upper(productType)  # for futures - for demo "SUSDT-FUTURES", for real "USDT-FUTURES"
    params["marginCoin"] = str.upper(marginCoin)    # for futures - for demo "SUSDT", for real "USDT"
    params["holdSide"] = str(holdSide)              # position direction: "long" or "short"
    params["amount"] = str(amount)                  # margin amount, positive means increase, negative means decrease

    # POST
    method = "POST"
    timestamp = get_timestamp()  # get_timestamp()
    request_path = "/api/v2/mix/account/set-margin"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def set_margin_mode(symbol, productType, marginCoin, marginMode='crossed'):
    params = dict()
    params["symbol"] = str.upper(symbol)            # trading pair, for example "SETHSUSDT"
    params["productType"] = str.upper(productType)  # for futures - for demo "SUSDT-FUTURES", for real "USDT-FUTURES"
    params["marginCoin"] = str.upper(marginCoin)    # for futures - for demo "SUSDT", for real "USDT"
    params["marginMode"] = str(marginMode)          # "crossed" or "isolated"

    # POST
    method = "POST"
    timestamp = get_timestamp()                     # get_timestamp()
    request_path = "/api/v2/mix/account/set-margin-mode"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def set_leverage(symbol, productType, marginCoin, leverage, holdSide = ""):
    params = dict()
    params["symbol"] = str.upper(symbol)            # trading pair, for example "SETHSUSDT"
    params["productType"] = str.upper(productType)  # for futures - for demo "SUSDT-FUTURES", for real "USDT-FUTURES"
    params["marginCoin"] = str.upper(marginCoin)    # for futures - for demo "SUSDT", for real "USDT"
    params["leverage"] = str(leverage)              # margin amount, positive means increase, negative means decrease
    params["holdSide"] = str(holdSide)              # position direction: "long" or "short" (ignore in crossed mode)

    # POST
    method = "POST"
    timestamp = get_timestamp()                     # get_timestamp()
    request_path = "/api/v2/mix/account/set-leverage"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


# Выставляем торговый ордер
def place_order(symbol, productType, marginCoin, size, side,
                marginMode='crossed', tp='', sl='', price='',
                tradeSide='', orderType = 'market', force='FOK', reduceOnly='NO'):

    params = dict()
    params["symbol"] = str.upper(symbol)                 # "SETHSUSDT"
    params["productType"] = str.upper(productType)       # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["marginMode"] = str.lower(marginMode)                     # crossed or isolated
    params["marginCoin"] = str.upper(marginCoin)         # for demo, for real USDT
    params["size"] = str(size)                           # position size
    params["price"] = str(price)
    params["side"] = str(side)                           # "sell" or "buy"
    params["tradeSide"] = str.lower(tradeSide)           # in hedge-mode: "open" or "close", in crossed - ignore
    params["orderType"] = str.lower(orderType)           # 'limit',
    params["force"] = str.upper(force)                   # IOC (Immediate or cancel), FOK (Fill or kill), GTC (Good till canceled),Post only
    params["clientOid"] = str(random.randint(0, 15000000))
    params["reduceOnly"] = str.upper(reduceOnly)         # 'YES' or 'NO'
    params["presetStopSurplusPrice"] = str(tp)           # TakeProfit
    params["presetStopLossPrice"] = str(sl)              # StopLoss

    # POST
    method = "POST"
    timestamp = get_timestamp()  # get_timestamp()
    request_path = "/api/v2/mix/order/place-order"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def flash_close_position(productType, symbol='', holdSide = ''):
    """if hold_side = '' - closes all positions
       For close specified - use "long" or "short" """

    params = dict()
    params["symbol"] = str.upper(symbol)             # "SETHSUSDT"
    params["productType"] = str.upper(productType)   # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["holdSide"] = str(holdSide)               # "long" or "short", or can be left blank for close all

    method = "POST"
    timestamp = get_timestamp()                      # get_timestamp()
    request_path = "/api/v2/mix/order/close-positions"
    body = json.dumps(params)
    signature = sign(pre_sign(timestamp, method, request_path, str(body)), API_SECRET)
    return make_request_post(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_server_time():
    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/public/time"
    body = ""

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_opened_positions(symbol, productType, marginCoin, openAmount, openPrice, leverage='20'):
    params = dict()
    params["symbol"] = str.upper(symbol)            # trading pair, for example "SETHSUSDT"
    params["productType"] = str.upper(productType)  # for futures - for demo "SUSDT-FUTURES", for real "USDT-FUTURES"
    params["marginCoin"] = str.upper(marginCoin)    # for futures - for demo "SUSDT", for real "USDT"
    params["openAmount"] = str(openAmount)          # Amount
    params["openPrice"] = str(openPrice)            # Price of the order
    params["leverage"] = str(leverage)              # Leverage, default 20

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/position/all-position"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_symbol_leverage_levels(symbol, productType):
    """In Bitget API docs - Get Position Tier"""
    params = dict()
    params["symbol"] = str.upper(symbol)  # trading pair, for example "SETHSUSDT"
    params["productType"] = str.upper(productType)  # for futures - for demo "SUSDT-FUTURES", for real "USDT-FUTURES"

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/query-position-lever"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_all_positions(productType, marginCoin):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["marginCoin"] = str.upper(marginCoin)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/position/all-position"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_single_position(productType, symbol, marginCoin):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["symbol"] = str.upper(symbol)
    params["marginCoin"] = str.upper(marginCoin)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/position/all-position"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_last_position_pnl(productType):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["limit"] = "1"

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/position/history-position"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)

    return response.json()['data']['list'][0]['netProfit']


def get_last_position(productType):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["limit"] = "1"

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/position/history-position"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)

    return response.json()['data']['list'][0]


def get_symbol_price(symbol, productType):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["symbol"] = str.upper(symbol)


    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/symbol-price"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    responce = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)
    return responce



def get_all_symbols_info(productType):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/tickers"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_contract_config(productType, symbol):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["symbol"] = str.upper(symbol)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/contracts"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


def get_candlestick_data(productType, symbol, granularity, limit):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["symbol"] = str.upper(symbol)
    params["granularity"] = str(granularity)
    params["limit"] = str(limit)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/candles"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body).json()
    if response['msg'] == "success":
        candlestick_data = response['data']
        data = []
        for candle in candlestick_data:
            candle = list(map(float, candle))
            data.append(candle)
        return data
    else:
        return None

def get_historical_candlestick_data(productType, symbol, granularity, limit):
    params = dict()
    params["productType"] = str.upper(productType)  # for demo "SUSDT-FUTURES", for real USDT-FUTURES
    params["symbol"] = str.upper(symbol)
    params["granularity"] = str(granularity)
    params["limit"] = str(limit)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/history-candles"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body).json()
    if response['msg'] == "success":
        candlestick_data = response['data']
        data = []
        for candle in candlestick_data:
            candle = list(map(float, candle))
            data.append(candle)
        return data
    else:
        return None


def get_pending_orders(productType, orderId='', clientOid='', symbol='',
                       status='', idLessThan='', startTime='', endTime='', limit=''):
    params = dict()
    params["orderId"] = str(orderId)                # Order ID; if both orderId and clientOid are entered, orderId prevails.
    params["clientOid"] = str(clientOid)            # Customize order ID; If both orderId and clientOid are entered, orderId prevails.
    params["symbol"] = str.upper(symbol)            # Trading pair, e.g. ETHUSDT
    params["productType"] = str.upper(productType)  # USDT-FUTURES, COIN-FUTURES, USDC-FUTURES (for demo with "s" - SUSDT)
    params["status"] = str.lower(status)            # If not specified, all ordered with a status of live (not filled yet) will be returned.
                                                    # partially_filled: Partially filled
    params["idLessThan"] = str(idLessThan)          # Requests the content on the page before this ID (older data),
                                                    # the value input should be the endId of the corresponding interface.
    params["startTime"] = str(startTime)            # Unix timestamp in milliseconds format, e.g. 1597026383085
                                                    # The maximum time span supported is three months.
                                                    # The default end time is three months if no value is set for the end time.
    params["endTime"] = str(endTime)                # Unix timestamp in milliseconds format, e.g. 1597026383085
                                                    # The maximum time span supported is three months.
                                                    # The default start time is three months ago if no value is set for the start time.
    params["limit"] = str(limit)                    # Number of queries: Maximum: 100, default: 100

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/order/orders-pending"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)



# Получить информацию обо всех счетах
def get_all_account_info():
    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/account/all-account-balance"
    body = ""

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


# Получить инфо о конкретном счете
def get_account_info(productType, symbol, marginCoin):
    params = dict()
    params["productType"] = str.upper(productType)  # {"symbol": "TRXUSDT", "marginCoin": "USDT"}
    params["symbol"] = str.upper(symbol)
    params["marginCoin"] = str.upper(marginCoin)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/account/account"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


# Get info about percentage of buy and sell positions
def get_long_short_ratio(symbol, period='5m'):
    params = dict()
    params["symbol"] = str.upper(symbol)
    params["period"] = str.lower(period)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/long-short"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)
    if response.json()['msg'] == 'success':
        return response
    else:
        print("Can't get long_short ratio!\n"
              f"Message: {response.json()['msg']}")
        return None


# Get info about volume of buy and sell positions
def get_long_short_volume(symbol, period='5m'):
    params = dict()
    params["symbol"] = str.upper(symbol)
    params["period"] = str.lower(period)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/taker-buy-sell"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)
    if response.json()['msg'] == 'success':
        return response
    else:
        print("Can't get long_short ratio!\n"
              f"Message: {response.json()['msg']}")
        return None


# Get merge depth data
def get_market_depth(productType, symbol, precision='scale0', limit='15'):
    params = dict()
    params["productType"] = str.upper(productType)  # {"symbol": "TRXUSDT", "marginCoin": "USDT"}
    params["symbol"] = str.upper(symbol)
    params["precision"] = str.lower(precision)      # Price accuracy, according to the selected accuracy as the step size
                                                    # to return the cumulative depth, enumeration value: scale0/scale1/scale2/scale3
    params["limit"] = str.lower(limit)              # Fixed gear enumeration value: 1/5/15/50/max, the default gear is 100

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/merge-depth"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    return make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)


# Get info about funding rate
def get_funding_rate(symbol, productType):
    params = dict()
    params["symbol"] = str.upper(symbol)
    params["productType"] = str.upper(productType)

    # GET
    method = "GET"
    timestamp = get_timestamp()
    request_path = "/api/v2/mix/market/current-fund-rate"
    body = ""
    request_path = request_path + parse_params_to_str(params)

    signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
    response = make_request_get(API_KEY, signature, PASSPHRASE, timestamp, request_path, body)
    if response.json()['msg'] == 'success':
        return response

    else:
        print("Can't get funding_rate!\n"
              f"Message: {response.json()['msg']}")
        return None



# # Place order in demo futures trading
# curl -X POST "https://api.bitget.com/api/v2/mix/order/place-order" \
# -H "ACCESS-KEY:*******" \
# -H "ACCESS-SIGN:*******" \
# -H "ACCESS-PASSPHRASE:*****" \
# -H "ACCESS-TIMESTAMP:1659076670000" \
# -H "locale:en-US" \
# -H "Content-Type: application/json" \
# -d '{
#     "symbol": "SETHSUSDT",
#     "productType": "susdt-futures",
#     "marginMode": "isolated",
#     "marginCoin": "SUSDT",
#     "size": "1.5",
#     "price": "2000",
#     "side": "buy",
#     "tradeSide": "open",
#     "orderType": "limit",
#     "force": "gtc",
#     "clientOid": "12121212122",
#     "reduceOnly": "NO",
#     "presetStopSurplusPrice": "2300",
#     "presetStopLossPrice": "1800"
# }'
#
# Request URI
#
# /api/v2/mix/order/place-order
# Method
#
# POST


# Account INFO
# GET /api/v2/mix/account/accounts
#
# curl "https://api.bitget.com/api/v2/mix/account/accounts?productType=USDT-FUTURES" \
#    -H "ACCESS-KEY:*******" \
#    -H "ACCESS-SIGN:*" \
#    -H "ACCESS-PASSPHRASE:*" \
#    -H "ACCESS-TIMESTAMP:1659076670000" \
#    -H "locale:en-US" \
#    -H "Content-Type: application/json"


# # GET
# method = "GET"
# body = ""
# request_path = "/api/v2/mix/account/account"
# params = {"symbol": "TRXUSDT", "marginCoin": "USDT"}
# request_path = request_path + parse_params_to_str(params)  # Need to be sorted in ascending alphabetical order by key
# signature = sign(pre_sign(timestamp, method, request_path, body), API_SECRET)
