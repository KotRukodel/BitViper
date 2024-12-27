from request_functions import *
from telegram_bot import bot_send_message


# Change Position mode
def set_position_mode_for_account(productType, symbol, marginCoin, position_mode):
    try:
        current_position_mode = get_account_info(productType, symbol, marginCoin).json()["data"]["posMode"]
        if current_position_mode:
            if current_position_mode == str.lower(position_mode):
                print(f"Position mode is already: {current_position_mode}")
                bot_send_message(f"Position mode is already: {current_position_mode}")
                return current_position_mode
            elif get_all_positions(productType, marginCoin).json()["data"] or \
                    get_pending_orders(productType).json()["data"]["entrustedList"]:
                print("Position mode can't be changed due to opened positions or orders")
                bot_send_message("Position mode can't be changed due to opened positions or orders")
                return current_position_mode
            else:
                response = set_position_mode(productType, position_mode)
                if response.status_code == 200 and response.json()['data']:
                    new_position_mode = response.json()['data']['posMode']
                    print(f"Position mode is successfully set to {new_position_mode}")
                    bot_send_message(f"Position mode is successfully set to {new_position_mode}")
                    return new_position_mode

                else:
                    print(response.status_code)
                    print(response.json()['msg'])
                    print(f"Position mode isn't set!\n"
                          f"{response.json()['msg']}")
                    bot_send_message(f"Position mode isn't set!\n"
                                     f"{response.json()['msg']}")
                    return current_position_mode
        else:
            print("No Position mode data!")
            bot_send_message("No Position mode data!")
            return None

    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Error processing Position mode: {symbol}: {e}")
        return None


def set_margin_mode_for_account(productType, symbol, marginCoin, margin_mode):
    try:
        current_margin_mode = get_account_info(productType, symbol, marginCoin).json()["data"]["marginMode"]
        if current_margin_mode:
            if current_margin_mode == str.lower(margin_mode):
                print(f"Margin mode is already: {current_margin_mode}")
                bot_send_message(f"Margin mode is already: {current_margin_mode}")
                return current_margin_mode
            elif get_single_position(productType, symbol, marginCoin).json()["data"] or \
                    get_pending_orders(productType, symbol=symbol).json()["data"]["entrustedList"]:
                print(f"Margin mode can't be changed due to opened positions or orders in {symbol}")
                bot_send_message(f"Margin mode can't be changed due to opened positions or orders in {symbol}")
                return current_margin_mode
            else:
                response = set_margin_mode(symbol, productType, marginCoin, margin_mode)
                if response.status_code == 200 and response.json()['data']:
                    new_margin_mode = response.json()['data']['marginMode']
                    # longleverage = response.json()['data']['longLeverage']
                    # shortleverage = response.json()['data']['shortLeverage']
                    print(f"Margin mode is successfully set to {new_margin_mode}")
                    bot_send_message(f"Margin mode is successfully set to {new_margin_mode}")

                    return new_margin_mode

                else:
                    print(response.status_code)
                    print(response.json()['msg'])
                    print(f"Margin mode isn't set!\n"
                          f"{response.json()['msg']}")
                    bot_send_message(f"Margin mode isn't set!\n"
                                     f"{response.json()['msg']}")
                    return current_margin_mode
        else:
            default_margin_mode = set_margin_mode(symbol, productType, marginCoin).json()['data']['marginMode']
            print("No Margin mode data! Set margin_mode to default: 'crossed'!")
            bot_send_message("No Margin mode data! Set margin_mode to default: 'crossed'!")
            return default_margin_mode

    except (KeyError, ValueError, TypeError, IndexError) as e:
        default_margin_mode = set_margin_mode(symbol, productType, marginCoin).json()['data']['marginMode']
        print(f"Error processing Margin mode: {symbol}: {e}"
              f"Set margin_mode to default: 'crossed'!")
        bot_send_message(f"Error processing Margin mode: {symbol}: {e}"
                         f"Set margin_mode to default: 'crossed'!")
        return default_margin_mode


def set_leverage_for_symbol(productType, symbol, marginCoin, leverage, margin_mode):
    account_info = {}
    contract_config = {}
    default_leverage = 2
    try:
        account_info = get_account_info(productType, symbol, marginCoin).json()["data"]
        contract_config = get_contract_config(productType, symbol).json()["data"]
    except (KeyError, ValueError, TypeError, IndexError) as e:
        print(f"Error processing Account and Contract info in set_leverage: {symbol}: {e}")
        bot_send_message(f"Error processing Account and Contract info in set_leverage: {symbol}: {e}")
        if margin_mode == "crossed":
            symbol_leverage = set_leverage(symbol, productType, marginCoin, default_leverage).json()['data']['crossMarginLeverage']
            print("Set Leverage to default!\n"
                  f"Leverage: {symbol_leverage}, Margin_mode: {margin_mode}")
            bot_send_message("Set Leverage to default!\n"
                             f"Leverage: {symbol_leverage}, Margin_mode: {margin_mode}")
            return symbol_leverage
        elif margin_mode == "isolated":
            set_leverage(symbol, productType, marginCoin, default_leverage, holdSide='short')
            symbol_leverage_long = set_leverage(symbol, productType, marginCoin, default_leverage, holdSide='long').json()['data']['longLeverage']
            print("Set Leverage to default!\n"
                  f"Leverage: {symbol_leverage_long}, Margin_mode: {margin_mode}")
            bot_send_message("Set Leverage to default!\n"
                             f"Leverage: {symbol_leverage_long}, Margin_mode: {margin_mode}")
            return symbol_leverage_long

    if account_info and contract_config:
        contract_config = contract_config[0]
        #margin_mode = account_info["marginMode"]
        min_symbol_leverage = int(contract_config['minLever'])
        max_symbol_leverage = int(contract_config['maxLever'])
        leverage = int(leverage)

        if margin_mode == "crossed":
            symbol_leverage = int(account_info["crossedMarginLeverage"])
            if leverage < min_symbol_leverage or leverage > max_symbol_leverage:
                print(f"Leverage is out of range:\n"
                      f"L: {leverage}, minL: {min_symbol_leverage}, maxL: {max_symbol_leverage}, margin_mode: {margin_mode}")
            elif leverage == symbol_leverage:
                print("Leverage is the same:\n"
                      f"L: {leverage}, accountL: {symbol_leverage}, margin_mode: {margin_mode}")
            else:
                symbol_leverage = set_leverage(symbol, productType, marginCoin, leverage).json()['data']['crossMarginLeverage']
                print(f"Leverage is successfully changed!\n"
                      f"Current_leverage: {symbol_leverage}, margin_mode: {margin_mode}")
            return symbol_leverage

        elif margin_mode == "isolated":
            symbol_leverage_long = int(account_info["isolatedLongLever"])
            symbol_leverage_short = int(account_info["isolatedShortLever"])
            if leverage < min_symbol_leverage or leverage > max_symbol_leverage:
                symbol_leverage = min(symbol_leverage_long, symbol_leverage_short)
                set_leverage(symbol, productType, marginCoin, symbol_leverage, holdSide='short')
                set_leverage(symbol, productType, marginCoin, symbol_leverage, holdSide='long')
                print(f"Leverage is out of range! Is set to min:\n"
                      f"L: {leverage}, minL: {min_symbol_leverage}, maxL: {max_symbol_leverage}, margin_mode: {margin_mode}")
                bot_send_message(f"Leverage is out of range! Is set to min:\n"
                                 f"L: {leverage}, minL: {min_symbol_leverage}, maxL: {max_symbol_leverage}, margin_mode: {margin_mode}")
                return symbol_leverage
            elif leverage == symbol_leverage_long and symbol_leverage_long == symbol_leverage_short:
                symbol_leverage = symbol_leverage_long
                print(f"Leverage is the same!\n"
                      f"LongLever: {symbol_leverage_long}, ShortLever: {symbol_leverage_short}, margin_mode: {margin_mode}")
                bot_send_message(f"Leverage is the same!\n"
                                 f"LongLever: {symbol_leverage_long}, ShortLever: {symbol_leverage_short}, margin_mode: {margin_mode}")
                return symbol_leverage
            elif leverage == symbol_leverage_long and leverage != symbol_leverage_short:
                symbol_leverage = set_leverage(symbol, productType, marginCoin, leverage, holdSide='short').json()['data']['shortLeverage']
                print(f"ShortLeverage is successfully changed!\n"
                      f"LongLever: {symbol_leverage_long}, ShortLever: {symbol_leverage}, margin_mode: {margin_mode}")
                bot_send_message(f"ShortLeverage is successfully changed!\n"
                                 f"LongLever: {symbol_leverage_long}, ShortLever: {symbol_leverage}, margin_mode: {margin_mode}")
                return symbol_leverage
            elif leverage == symbol_leverage_short and leverage != symbol_leverage_long:
                symbol_leverage = set_leverage(symbol, productType, marginCoin, leverage, holdSide='long').json()['data']['longLeverage']
                print(f"LongLeverage is successfully changed!\n"
                      f"LongLever: {symbol_leverage}, ShortLever: {symbol_leverage_short}, margin_mode: {margin_mode}")
                bot_send_message(f"LongLeverage is successfully changed!\n"
                                 f"LongLever: {symbol_leverage}, ShortLever: {symbol_leverage_short}, margin_mode: {margin_mode}")
                return symbol_leverage
    else:
        print("No data available on account_info and contract_config")
        bot_send_message("No data available on account_info and contract_config")
        if margin_mode == "crossed":
            symbol_leverage = set_leverage(symbol, productType, marginCoin, default_leverage).json()['data']['crossMarginLeverage']
            print("Set Leverage to default!\n"
                  f"Leverage: {symbol_leverage}, Margin_mode: {margin_mode}")
            bot_send_message("Set Leverage to default!\n"
                             f"Leverage: {symbol_leverage}, Margin_mode: {margin_mode}")
            return symbol_leverage
        elif margin_mode == "isolated":
            set_leverage(symbol, productType, marginCoin, default_leverage, holdSide='short')
            symbol_leverage_long = set_leverage(symbol, productType, marginCoin, default_leverage, holdSide='long').json()['data']['longLeverage']
            print("Set Leverage to default!\n"
                  f"Leverage: {symbol_leverage_long}, Margin_mode: {margin_mode}")
            bot_send_message("Set Leverage to default!\n"
                             f"Leverage: {symbol_leverage_long}, Margin_mode: {margin_mode}")
            return symbol_leverage_long


def change_position_margin(symbol, productType, marginCoin, new_trade, new_margin_mode, result_predict, trade_equity):
    if new_trade and new_margin_mode == "isolated":
        if result_predict == 'BUY':
            chg_margin = adjust_position_margin(symbol, productType, marginCoin, 'long', trade_equity)
            if chg_margin.json()['msg'] == 'success':
                print("Position margin is adjusted!\n "
                      f"Symbol: {symbol}, Pos_Side: {result_predict}, Margin_Adjustment: {trade_equity}")
                bot_send_message("Position margin is adjusted!\n "
                                 f"Symbol: {symbol}, Pos_Side: {result_predict}, Margin_Adjustment: {trade_equity}")
        elif result_predict == 'SELL':
            adjust_position_margin(symbol, productType, marginCoin, 'short', trade_equity)
            print("Position margin is adjusted!\n "
                  f"Symbol: {symbol}, Pos_Side: {result_predict}, Margin_Adjustment: {trade_equity}")
            bot_send_message("Position margin is adjusted!\n "
                             f"Symbol: {symbol}, Pos_Side: {result_predict}, Margin_Adjustment: {trade_equity}")
        else:
            print("Can't change position margin!\n"
                  f"Symbol: {symbol}, Result_predict: {result_predict}")
    else:
        print("No need to change position_margin!\n"
              f"New_trade: {new_trade}, Margin: {new_margin_mode}")













# Change Leverage(), if leverage >= max -> apply max, if not leverage


# Adjust Position Margin (add or reduce margin in isolated mode)
# Get All orders
