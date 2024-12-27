# Bitget Trading Bot

An automated cryptocurrency trading bot for Bitget exchange that implements custom trading strategies using TradingView technical analysis, based on convenient and flexible risk management and position management, and real-time websocket data. 

## Features

- Real-time market data processing via Bitget WebSocket API
- Custom trading strategies based on TradingView Technical Analysis
- Automated position management with stop-loss and take-profit
- Risk management with configurable trade sizing
- Support for both crossed and isolated margin modes
- Flexible leverage settings
- Position mode selection (one-way/hedge)

## Prerequisites

- Python 3.7+
- Bitget API credentials
- TradingView Technical Analysis library

## Installation

No need any special installation.

## Configuration

Configure file config.py with your API credentials and trading parameters in main.py:

```python
# General Settings
PRODUCTTYPE = "SUSDT-FUTURES"    # Account type
MARGINCOIN = "SUSDT"            # Margin currency
VOLUME = 1000000                # Min trading volume threshold
LEVERAGE = 10                   # Default leverage (10x-125x)

# Risk Management
TRADE_RISK = 0.03              # Risk per trade (3%)
RR = 1.5                       # Risk/Reward ratio

# Trading Intervals
GRANULARITY = '5m'             # Candle interval
LIMIT = '4'                    # Number of candles to analyze
```

## WebSocket Integration

The bot uses three main WebSocket connections:

1. Private data stream for account/position updates:
```python
await websocket_private_data(PRODUCTTYPE, private_queue, pos_check_queue)
```

2. Public market data stream:
```python
await websocket_public_data(PRODUCTTYPE, subscr_queue, public_queue, pos_check_queue)
```

3. Subscription management:
```python
await manage_websocket_public_subscriptions(subscr_queue, pos_check_queue)
```

## Trading Strategy Implementation

Use current startegies or add custom ones in the `strategies.py` file:

```python
async def tradingviewTA_candleSpike(exchange, interval, product_type, granularity, limit, volume, symb_def):
    # Implement your trading logic here
    return SYMBOL, RESULT_PREDICT
```

## Position Management

The bot includes comprehensive position management:

- Automatic stop-loss and take-profit calculation
- Position sizing based on account risk parameters
- Real-time position monitoring and updates
- Automatic position closure based on defined criteria

## Usage

1. Set up your configuration parameters in config.py
2. Run the bot:

```bash
python main.py
```

## Risk Warning

This software is for educational purposes only. Cryptocurrency trading carries significant risk. Always test with small amounts first and never trade more than you can afford to lose.

## License

MIT
