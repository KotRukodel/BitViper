import asyncio

from analysis import trade_tradingview_ta
from analysis import trade_candlestick_analysis
from request_functions import get_all_symbols_info
from utility import check_symbol_status
import time


#Достаем наиболее торгуемую монету за последние 24 часа
def get_max_traded_symbols(PRODUCTTYPE, VOLUME):
    all_symbols = get_all_symbols_info(PRODUCTTYPE).json()
    all_symbol_change = {}
    #all_symbol_volume = {}
    for symbol in all_symbols['data']:
        if float(symbol['quoteVolume']) >= VOLUME:
            all_symbol_change[f'{symbol['symbol']}'] = abs(float(symbol['changeUtc24h']))
            #all_symbol_volume[f'{symbol['symbol']}'] = float(symbol['baseVolume']) * float(symbol['lastPr'])

    sorted_all_symbol_change = sorted(all_symbol_change.items(), key=lambda item: item[1], reverse=True)

    #symbol_max_change = max(all_symbol_change, key=all_symbol_change.get)
    #symbol_max_volume = max(all_symbol_volume, key=all_symbol_volume.get)
    #max_change = all_symbol_change[f'{symbol_max_change}']
    #max_volume = all_symbol_volume[f'{symbol_max_volume}']

    return sorted_all_symbol_change  #symbol_max_change, max_change #symbol_max_volume, max_volume


#Получаем параметры для совершения сделки
async def get_trade_parameters(EXCHANGE, INTERVAL, PRODUCTTYPE, GRANULARITY, LIMIT, VOLUME, SYMB_DEF):
    SYMBOL = ''
    predict_tradingview = ''
    predict_candle_spike = ''

    while True:
        try:
            # Fetch the symbols with the highest trading volume and activity
            MAX_TRADED_SYMBOLS = get_max_traded_symbols(PRODUCTTYPE, VOLUME)
        except Exception as e:
            print(f"Error fetching max traded symbols: {e}"
                  f"Got the following default symbols: {SYMB_DEF}")
            MAX_TRADED_SYMBOLS = SYMB_DEF
            return MAX_TRADED_SYMBOLS

        for symbol in MAX_TRADED_SYMBOLS:
            SYMBOL = symbol[0]
            print(f"Самые активные символы:\n"
                  f"{MAX_TRADED_SYMBOLS}")
            # Check whether symbol is available for trading
            symbol_status = check_symbol_status(PRODUCTTYPE, SYMBOL)
            if symbol_status and symbol_status == 'normal':

                # Perform analysis using different analysis tactics from analysis.py
                #strategies_list = []
                predict_tradingview = trade_tradingview_ta(SYMBOL, EXCHANGE, INTERVAL)
                predict_candle_spike = trade_candlestick_analysis(PRODUCTTYPE, SYMBOL, GRANULARITY, LIMIT)
                if not predict_tradingview:  #or not predict_candle_spike:
                    print(f"Нет Tradingview прогноза по символу {SYMBOL}:\n"
                          f"TV: {predict_tradingview} Candles: {predict_candle_spike}")
                    await asyncio.sleep(10)
                    continue
                # elif predict_tradingview and not predict_candle_spike:
                #     print(f"Нет прогноза по символу {SYMBOL}:\n"
                #           f"TV: {predict_tradingview} Candles: {predict_candle_spike}")
                #     time.sleep(60)
                #     continue
                elif predict_tradingview and "STRONG" in predict_tradingview:  #predict_candle_spike or
                    print(f"Успешно получен прогноз STRONG по символу {SYMBOL}:\n"
                          f"TV: {predict_tradingview} Candles: {predict_candle_spike}")
                    # Break out of the loop if a symbol applied successfully
                    break

                elif predict_tradingview and predict_candle_spike:
                    print(f"Прогнозы по символу {SYMBOL} успешно получены:\n"
                          f"TV: {predict_tradingview} Candles: {predict_candle_spike}")
                    # Break out of the loop if a symbol applied successfully
                    break
                else:
                    print("Tradingview не STRONG или нет candles прогноза!\n"
                          f"TV: {predict_tradingview} Candles: {predict_candle_spike}")
                    await asyncio.sleep(60)#time.sleep(60)
                    continue

            else:
                continue
        # If both predict_tradingview and predict_candle_spike are not None or "STRONG" in TV prediction,
        # break the While loop
        if (predict_tradingview and "STRONG" in predict_tradingview) or \
                (predict_tradingview and predict_candle_spike):
            break

    return SYMBOL, predict_tradingview, predict_candle_spike
