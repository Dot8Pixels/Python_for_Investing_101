import secrets
import pandas as pd
import mplfinance as mpf
import numpy as np
from pandas_datareader import data as web
import yfinance as yf
yf.pdr_override()
import vectorbt as vbt
from datetime import datetime
from binance.client import Client
import os
import pandas_ta as ta

import sys
sys.path.append(r'C:\Users\gunsr\Desktop\Programming\Git_Remote\Investic\Python-for-Investing-101\Global_Config')
import api_key

bn_key = api_key.binance_api_key
bn_secret = api_key.binance_api_secret

column_names = ["strategy", "condition", "parameters", "total_return", "max_drawdown", "winrate"]
global_log_df = pd.DataFrame(columns=column_names)

def get_data(ls_tickers, api_key, api_secret):
    
    client = Client(api_key, api_secret)
    
    ls_df = []
    
    for ticker in ls_tickers:
        klines = client.get_historical_klines(ticker, Client.KLINE_INTERVAL_1DAY, "2000 day ago UTC")
        data = pd.DataFrame(klines)
        data.columns = ['open_time', 
                        'Open', 
                        'High', 
                        'Low',
                        'Close', 
                        'Volume',
                        'close_time',
                        'quote_asset_volume',
                        'number_of_trades',
                        'taker_buy_base_asset_volume',
                        'take_buy_quote_asset_volume',
                        'can_be_ignored']
        
        data['Date'] = pd.to_datetime(data['open_time'], unit='ms')
        df = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.astype({"Open": float, 
                        "High": float, 
                        "Low": float, 
                        "Close": float, 
                        "Volume": float})
        df = df.rename(columns = {  'Date': 'date',
                                    'Open': 'open', 
                                    'High': 'high', 
                                    'Low': 'low', 
                                    'Close': 'close',
                                    'Volume': 'volume'}, 
                                    inplace = False)
        df['chg'] = df['close'].pct_change() * 100
        ls_df.append(df)
        
    return ls_df

def backtest_vectorbt(df):

    df = df.set_index('date')

    df.ta.tsignals(df.signal, asbool=True, append=True)
    
    df['action_price'] = df['open'].shift(-1)
    # print(df)

    trades_table = df.iloc[: -5][df.TS_Trades != 0]
    trades_table['return'] = trades_table['action_price'].pct_change()
    
    trades_summary = trades_table.loc[trades_table.TS_Exits == True]

    return df

def multi_macd_str(df, fast_macd, slow_macd):
    for i in fast_macd:
        for j in slow_macd:
            if i != j:
                new_df = df.copy()

                new_df.ta.macd(i, j, append=True)
                new_df['signal'] = new_df.iloc[:,-3] > new_df.iloc[:, -2]

                tsignal_df = backtest_vectorbt(new_df)

                get_return(tsignal_df, "MACD", "MACD > Signal", f"Fast: {i}, Slow: {j}")

                print("MACD")
                print(f"fast: {i}, slow: {j}")
                "------------------------------------------------\n"

def multi_action_zone_str(df, fast_macd, slow_macd):
    for i in fast_macd:
        for j in slow_macd:
            if i != j:
                new_df = df.copy()

                new_df.ta.macd(i, j, append=True)
                new_df['signal'] = new_df.iloc[:,-3] > 0

                tsignal_df = backtest_vectorbt(new_df)

                get_return(tsignal_df, "Action Zone", "MACD > 0", f"Fast: {i}, Slow: {j}")

                print("Action Zone")
                print(f"fast: {i}, slow: {j}")
                "------------------------------------------------\n"

def get_return(df, strategy_name, condition, parameters_detail):

    global global_log_df

    port = vbt.Portfolio.from_signals(df.close,
                                    entries=df.TS_Entries,
                                    exits=df.TS_Exits,
                                    freq="D",
                                    init_cash=100000,
                                    fees=0.0025,
                                    slippage=0.0025)

    port_stats = port.stats()

    with open('logs/backtest_log.txt', 'a+') as f:
        f.write(f"Strategy: {strategy_name}\n")
        f.write(f"Condition: {condition}\n")
        f.write(parameters_detail+"\n")
        f.write(f"Total Return [%]: {port_stats[5]}\n")
        f.write(f"Max Drawdown [%]: {port_stats[9]}\n")
        f.write(f"Win Rate [%]: {port_stats[15]}\n")
        f.write("------------------------------------------------\n")

        input_df = pd.DataFrame({"strategy": [strategy_name],
                                "condition": [condition],
                                "parameters": [parameters_detail],
                                "total_return": [port_stats[5]], 
                                 "max_drawdown": [port_stats[9]], 
                                 "winrate": [port_stats[15]]})

        global_log_df = global_log_df.append(input_df, ignore_index=True)

if __name__ == "__main__":

    ls_tickers = ['BTCUSDT']

    ls_df = []

    ls_df = get_data(ls_tickers, bn_key, bn_key)

    fast_macd = 12
    slow_macd = 26

    for idx, data in enumerate(ls_df):
        print(ls_tickers[idx])
        print(data)
        
        fast_macd = [*range(5, 27, 1)]
        slow_macd = [*range(5, 27, 1)]

        # fast_macd = [5,7,10,12,15,20,23,26]
        # slow_macd = [5,7,10,12,15,20,23,26]

        multi_macd_str(data, fast_macd, slow_macd)

        multi_action_zone_str(data, fast_macd, slow_macd)

        global_log_df = global_log_df.sort_values(by=['total_return', 
                                                        'max_drawdown', 
                                                        'winrate'], 
                                                    ascending=[False, 
                                                                True,
                                                                False])
        global_log_df.to_csv("./logs/backtest_df_log.csv", header=True, mode="w+")
        print(global_log_df)
    

    print(" --- Done ---")



