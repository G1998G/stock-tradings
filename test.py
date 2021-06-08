import json
import pandas as pd
import pprint
import requests
import numpy as np
from datetime import datetime as dt,timedelta,timezone
import time
import matplotlib.pyplot as plt
import pybitflyer

api = pybitflyer.API()

#cryptocompareのAPIを活用して、最初の20回分を取得する。
def init_data(span):
    df = pd.DataFrame()
    if span == 'second':
        print('initで秒指定はできません。空のdfを返します')
        return df
    payload={'fsym': "BTC", 'tsym': "JPY", 'limit':20}
    URL = "https://min-api.cryptocompare.com/data/histo" + span
    #histohour == 1時間スパン
    #histoday == 1日スパン
    #histominute == 1分スパン
    r = requests.get(URL, params=payload)
    j = r.json()
    for d in j["Data"]:
        t = dt.fromtimestamp(d['time'])
        ctx = pd.Series( {'time':t,'close':d['close']})
        df = df.append(ctx,ignore_index=True )
    print(df)
    return df

def eval_span(func):
    def deco(**k):
        if k['span'] == 'day':
            pass
        elif k['span'] == 'hour':
            pass
        elif k['span'] == 'minute':
            time.sleep(50) 
            while True: 
                if dt.now().strftime('%S') [0:2]== '00':
                    ret = func(**k)
                    return ret
    return deco

@eval_span
def bitfliyer(df,span,maxamount=40):
    d = api.ticker(product_code = "BTC_JPY")
    timestr = d['timestamp'][0:-4]
    t = dt.strptime(timestr, '%Y-%m-%dT%H:%M:%S')+ timedelta(hours=9)
    ticker = pd.Series( {'time':t,'close':d['ltp']})
    df = df.append(ticker,ignore_index=True)
    #maxamountを超えた場合、古いデータから削除する。*メモリ節約のため
    if len(df.index) >=maxamount:
        df = df.drop(0)
        df = df.reset_index(drop=True)
    #print(df)
    return df

@eval_span
def coincheck(df,span,maxamount=40):
    URL = 'https://coincheck.com/api/ticker'
    d = requests.get(URL).json()
    t = dt.fromtimestamp(d['timestamp'])
    ticker = pd.Series( {'time':t,'close':d['last']})
    df = df.append(ticker,ignore_index=True)
    if len(df.index) >=maxamount:
        df = df.drop(0)
        df = df.reset_index(drop=True)
    #print(df)
    return df

def make_bband(df):
    bband = df
    # ボリンジャーバンドの計算
    bband['mean'] = bband['close'].rolling(window=20).mean()
    bband['std'] = bband['close'].rolling(window=20).std()
    bband['upper'] = bband['mean'] + (bband['std'] * 2) #-2シグマ
    bband['lower'] = bband['mean'] - (bband['std'] * 2) #-2シグマ
    # ボリンジャーバンド%Bの計算
    bband['%B'] = (bband['close']-bband['lower']) / (bband['upper']-bband['lower'])
    pprint.pprint(bband)
    return bband

# macdの計算
def make_macd(df):
    macd = df

# Matplotlibでボリンジャーバンド描写する
def makefigure(bband):
    bband.set_index('time',inplace=True)
    bband[['close', 'mean', 'upper', 'lower']].plot()
    plt.title('20 Bollinger Band')
    plt.show()

def df_pros(df,*args):
    for arg in args:
        df = arg(df)
    return df

def main():   
    df = init_data('minute')
    df = df_pros(df,make_bband)
    while True:
        df = coincheck(df=df,span='minute',maxamount=100)
        df = df_pros(df,make_bband)
        yield df


if __name__ == "__main__":
    buytime =[]
    selltime = []
    lasttrade = 'sell'
    for  df in  main():
        print(f'lasttrade={lasttrade}')
        # 買う時
        if lasttrade == 'sell':
            # 直近3分で見たMACDの傾きが正
            # 
            if df.iloc[-1]['%B']< 0.15 and df.iloc[-2]['%B'] + 0.1 < df.iloc[-1]['%B']:
                print('買い!')
                buytime.append(df.iloc[-1]['time'])
                lasttrade = 'buy'
            # ボリンジャーバンド％が-0.2以下の時は問答無用で買い
            elif df.iloc[-1]['%B']< -0.15:
                print('買い!')
                buytime.append(df.iloc[-1]['time'])
                lasttrade = 'buy'

        if lasttrade =='buy':
            # ボリンジャーバンド%が0.8を超えたのち下落2回目の場合は問答無用で売り
            if df.iloc[-1]['%B'] > 0.80 and df.iloc[-2]['%B'] > df.iloc[-1]['%B'] and df.iloc[-3]['%B'] > df.iloc[-1]['%B'] and df.iloc[-4]['%B'] > df.iloc[-1]['%B']: 
                print('売り!')
                selltime.append(df.iloc[-1]['time'])
                lasttrade = 'sell'


