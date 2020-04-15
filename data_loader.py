import yfinance as yf
import pandas as pd

if __name__ == '__main__':
    yf.download(tickers="AAPL", period="7d", interval="1m").to_csv('data.csv')

    data = pd.read_csv('data.csv', sep=r'\s*,\s*',header=0, encoding='ascii', engine='python')

    data['Datetime'] = data['Datetime'].apply(lambda x: str(x)[0:19])

    data.to_csv('data.csv', sep=',',header=0,encoding='ascii')