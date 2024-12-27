import asyncio
import time
from trade_parameters import get_trade_parameters
from money_management import lot_count, sl_tp_count

# Strategy, based on TradingView_TA Summary and Candlestick Spike analysis
async def tradingviewTA_candleSpike(EXCHANGE, INTERVAL, PRODUCTTYPE, GRANULARITY, LIMIT, VOLUME, SYMB_DEF):

    while True:
        SYMBOL, predict_tradingview, predict_candle_spike = await get_trade_parameters(EXCHANGE, INTERVAL, PRODUCTTYPE,
                                                                                       GRANULARITY, LIMIT, VOLUME, SYMB_DEF)

        predicts = [predict_tradingview, predict_candle_spike]

        if ("BUY" in predicts[0] and predicts[1] == "BUY") or \
           ("BUY" in predicts[0] and predicts[1] == "NEUTRAL") or \
                (predicts[1] == "BUY" and predicts[0] == "NEUTRAL"):
            RESULT_PREDICT = "BUY"
            print(f"Получен общий прогноз: {RESULT_PREDICT} по символу {SYMBOL}")
            return SYMBOL, RESULT_PREDICT

        elif ("SELL" in predicts[0] and predicts[1] == "SELL") or \
             ("SELL" in predicts[0] and predicts[1] == "NEUTRAL") or \
                (predicts[1] == "SELL" and predicts[0] == "NEUTRAL"):
            RESULT_PREDICT = "SELL"
            print(f"Получен общий прогноз: {RESULT_PREDICT} по символу {SYMBOL}")
            return SYMBOL, RESULT_PREDICT

        else:
            print("Прогнозы не соответствуют стратегии: \n"
                  f"TV: {predicts[0]}, Candles: {predicts[1]}")
            await asyncio.sleep(60)#time.sleep(60)









