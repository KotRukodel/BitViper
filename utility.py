import json

from request_functions import get_contract_config, get_symbol_leverage_levels, get_symbol_price
from telegram_bot import bot_send_message


######################################################################
# For trading
######################################################################

# Converts to Symbol without "s"
def convert_usdt_symbol(symbol):
    symbol_c = str.upper(symbol)
    if symbol_c.endswith("SUSDT"):
        # Удаляем первый символ "S" и заменяем "SUSDT" на "USDT"
        return symbol_c[1:].replace("SUSDT", "USDT")
    return symbol_c


# Приводит кол-во знаков после запятой в цене к соответсвующему спецификации контракта
def convert_price_to_symbol(productType, symbol, price):
    try:
        response = get_contract_config(productType, symbol).json()
        data = response['data']
        if len(data) > 0:
            digits = int(data[0]['pricePlace'])
            converted_price = round(float(price), digits)
            return converted_price
        else:
            raise IndexError("Data list is empty.")
    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Error processing symbol: {symbol} lot : {e}")
        return float(price)  # значение по умолчанию


# Приводит кол-во знаков после запятой в лотах к соответсвующему спецификации контракта
def convert_lot_to_symbol(productType, symbol, lot):
    try:
        response = get_contract_config(productType, symbol).json()
        data = response['data']
        if len(data) > 0:
            digits = int(data[0]['volumePlace'])
            converted_volume = round(float(lot), digits)
            return converted_volume
        else:
            raise IndexError("Data list is empty.")
    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Error processing symbol: {symbol} lot : {e}")
        return float(lot)  # значение по умолчанию


# Проверяем лот на соответствие мин и макс лоту по символу
def check_min_max_lot(productType, symbol, lot, trade_equity, trade_risk, leverage, delta_sl, pff):
    contract_conf_response = get_contract_config(productType, symbol).json()
    symbol_levels_response = get_symbol_leverage_levels(symbol, productType).json()
    symbol_price_response = get_symbol_price(symbol, productType).json()
    if 'data' not in contract_conf_response or not contract_conf_response['data'] or \
            'data' not in symbol_levels_response or not symbol_levels_response['data'] or \
            'data' not in symbol_price_response or not symbol_price_response['data']:
        new_lot = ''
        print(f"No contract configuration, levels or prices found for {symbol}!")
        bot_send_message(f"No contract configuration, levels or prices found for {symbol}!")
        return new_lot
    else:
        contract_conf = contract_conf_response['data'][0]
        levels_list = symbol_levels_response['data']
        prices = symbol_price_response['data'][0]

        # get and check minimal requirements of the Exchange for opening position
        min_lot = (float(contract_conf['minTradeNum']) +         # min lot required
                   float(contract_conf['sizeMultiplier']))
        min_usdt = float(contract_conf['minTradeUSDT'])          # min volume required
        open_fee_rate = float(contract_conf['takerFeeRate'])     # fee rate for open position
        tfff = float(contract_conf['feeRateUpRatio'])            # transaction fee fluctuation factor

        last_price = float(prices['price'])                      # symbol last price
        trade_value = lot * last_price                           # trade volume of the lot in USDT
        account_equity = trade_equity / trade_risk               # available account equity for opening position
        open_fee = open_fee_rate * trade_value                   # fee for opening position of the trade_value
        initial_margin_for_position = (trade_value / leverage) * (1 + pff) + open_fee * (1 + tfff)

        if lot >= min_lot and trade_value >= min_usdt:
            if account_equity >= initial_margin_for_position:
                # check the maximum requirements of the Exchange for opening position
                level_max_list = []
                # level_min_list = []
                for level in levels_list:
                    if int(level['leverage']) == leverage:
                        level_max = int(level['endUnit'])
                        # level_min = int(level['startUnit'])
                        level_max_list.append(level_max)
                        # level_min_list.append(level_min)

                # min_usdt_level = min(level_min_list)
                max_usdt_level = max(level_max_list)
                # max_lot = max_usdt_level / last_price

                if max_usdt_level >= trade_value:  # max_lot >= lot:  # max_usdt_level >= trade_value:  # >= min_usdt_level:
                    new_lot = convert_lot_to_symbol(productType, symbol, lot)
                    print("Lot is successfully verified!\n"
                          f"Symbol: {symbol}, Lot: {new_lot}")
                    bot_send_message("Lot is successfully verified!\n"
                                     f"Symbol: {symbol}, Lot: {new_lot}")
                    return new_lot

                elif max_usdt_level < trade_value:  # max_lot < lot:  # max_usdt_level < trade_value:
                    new_lot_count = max_usdt_level / last_price
                    new_trade_risk = (new_lot_count * delta_sl) / account_equity
                    print("Trade_value is greater than allowed for this symbol and leverage!\n"
                          f"Symbol: {symbol}, Trade_value: {int(trade_value)}, Max_value: {max_usdt_level}")
                    bot_send_message("Trade_value is greater than allowed for this symbol and leverage!\n"
                                     f"Symbol: {symbol}, Trade_value: {int(trade_value)}, Max_value: {max_usdt_level}")
                    if new_trade_risk <= trade_risk:
                        new_lot = convert_lot_to_symbol(productType, symbol, new_lot_count)
                        print("New_trade_risk <= initial trade_risk!\n"
                              f"Symbol: {symbol}, New_lot: {new_lot},\n"
                              f" New_trade_risk: {round(new_trade_risk, 2)}, Trade_risk: {round(trade_risk, 2)}")
                        bot_send_message("New_trade_risk <= initial trade_risk!\n"
                                         f"Symbol: {symbol}, New_lot: {new_lot},\n"
                                         f" New_trade_risk: {round(new_trade_risk, 2)}, Trade_risk: {round(trade_risk, 2)}")
                        return new_lot
                    else:
                        new_lot = ''
                        print("New_trade_risk exceeds initial trade_risk!\n"
                              f"Symbol: {symbol}, New_lot: 0,\n"
                              f" New_trade_risk: {round(new_trade_risk, 2)}, Trade_risk: {round(trade_risk, 2)}")
                        bot_send_message("New_trade_risk exceeds initial trade_risk!\n"
                                         f"Symbol: {symbol}, New_lot: 0,\n"
                                         f" New_trade_risk: {round(new_trade_risk, 2)}, Trade_risk: {round(trade_risk, 2)}")
                        return new_lot
            else:
                new_lot = ''
                print("Account equity is less than Initial margin!"
                      f"Symbol: {symbol}, Lot: {lot}, New_lot: 0")
                bot_send_message("Account equity is less than Initial margin!"
                                 f"Symbol: {symbol}, Lot: {lot}, New_lot: 0")
                return new_lot
        else:
            print(f"Lot is less than min_lot!\n"
                  f"Symbol: {symbol}, Lot: {lot}, Min_lot: {min_lot}")
            bot_send_message(f"Lot is less than min_lot!\n"
                             f"Symbol: {symbol}, Lot: {lot}, Min_lot: {min_lot}")
            trade_value = min_lot * last_price  # trade volume of the lot in USDT
            open_fee = open_fee_rate * trade_value  # fee for opening position of the trade_value
            initial_margin_for_position = (trade_value / leverage) * (1 + pff) + open_fee * (1 + tfff)
            if account_equity >= initial_margin_for_position and trade_value >= min_usdt:
                new_risk = round((((min_lot * float(delta_sl)) / account_equity)*100), 2)
                new_lot = min_lot
                print("Take min_lot! Be sure to control Risk and increase Leverage!\n"
                      f"Risk: {new_risk}%, Leverage: {leverage}")
                bot_send_message("Take min_lot! Be sure to control Risk and increase Leverage!\n"
                                 f"Risk: {new_risk}%, Leverage: {leverage}")
                return new_lot
            else:
                new_lot = ''
                print("Insufficient funds for min_lot! Increase leverage or add funds!\n"
                      f"Symbol: {symbol}, Equity: {account_equity}\n"
                      f"Init_marg: {initial_margin_for_position}, Leverage: {leverage}")
                bot_send_message("Insufficient funds for min_lot! Increase leverage or add funds!\n"
                                 f"Symbol: {symbol}, Equity: {account_equity}\n"
                                 f"Init_marg: {initial_margin_for_position}, Leverage: {leverage}")
                return new_lot


# def check_lot_leverage_level(productType, symbol):
#     response = get_symbol_leverage_levels(symbol, productType).json()
#     symbol_levels_list = response['data']
#
#     for level in symbol_levels_list:
#         if lo


# Проверяем, можно ли торговать символом
def check_symbol_status(productType, symbol):
    contract_conf_response = get_contract_config(productType, symbol).json()
    if 'data' not in contract_conf_response or not contract_conf_response['data']:
        print(f"No contract configuration found for {symbol}")
        status = ''

    else:
        contract_conf = contract_conf_response['data'][0]
        status = contract_conf['symbolStatus']
        if status == 'normal':
            print(f'Cимвол {symbol} доступен для торговли!')
        else:
            print(f'Торговля по символу {symbol} ограничена!\n'
                  f'Статус: {status}')
    return status


# Clear Websocket queue
async def clear_queue(queue):
    while not queue.empty():
        await queue.get()
        queue.task_done()
    if queue.empty():
        print("Queue is successfully cleared!")




