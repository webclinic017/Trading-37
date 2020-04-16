from __future__ import (absolute_import,
                        division,
                        print_function,
                        unicode_literals)

import yfinance as yf
import pandas as pd

import trendln as tl
import backtrader as bt

class Strategy(bt.Strategy):
    params = (
        ('timeframe', 60),
        ('printlog', True)
    )

    wins = 0
    loses = 0

    def log(self, data, txt, doprint=False):
        if self.params.printlog or doprint:
            datetime = data.datetime
            date = datetime.date(0)
            time = datetime.time(0)
            print('%s, %s, %s' % (date, time, txt))

    def next(self):
        if len(self) < self.params.timeframe: return

        for dataindex, data in enumerate(self.datas):
            hasOrder = False
            for order in self.broker.get_orders_open():
                if order.data == data: hasOrder = True
            if hasOrder: continue

            lowdata = []
            highdata = []
            closedata = []

            for i in range(-self.params.timeframe, 1):
                lowdata.append(data.low[i])
                highdata.append(data.high[i])
                closedata.append(data.close[i])

            (_, _, c_mintrend, _), (_, _, c_maxtrend, _) = tl.calc_support_resistance(closedata[:self.params.timeframe-1])
            (_, _, lh_mintrend, _), (_, _, lh_maxtrend, _) = tl.calc_support_resistance((lowdata[:self.params.timeframe-1],
                                                                                                     highdata[:self.params.timeframe-1]))

            sell_buy_prediction = self.sell_buy_prediction(closedata,
                                                           closedata,
                                                           self.params.timeframe,
                                                           c_mintrend,
                                                           c_maxtrend)

            position = self.getposition(data=data, broker=self.broker)

            shouldSell = position and sell_buy_prediction[0]
            shouldBuy = not position and sell_buy_prediction[1]

            if shouldSell:
                self.sell(data=data, size=position.size)
                self.log(data, 'Sold data #{0} for {1}'.format(dataindex, closedata[self.params.timeframe]))
            elif shouldBuy:
                self.buy(data=data, price=2000.0)
                self.log(data, 'Bought data #{0} for {1}'.format(dataindex, closedata[self.params.timeframe]))

    def notify_trade(self, trade):
        if not trade.isclosed: return

        if trade.pnl >= 0:
            self.wins += 1
        else:
            self.loses += 1

        self.log(trade.data, 'Operation profit: %.2f' % trade.pnl)

    def start(self):
        print('Start cash: %.2f' % (self.broker.getvalue()))

    def stop(self):
        print('End cash: %.2f' % (self.broker.getvalue()))
        print('Win ratio: %.2f' % (self.wins/(self.wins+self.loses)))

    def sell_buy_prediction(self, buydata, selldata, timeframe, mintrend, maxtrend):

        shouldSell = False
        shouldBuy = False

        if mintrend:
            sellConfidence = 0
            price = selldata[timeframe]
            for trend in mintrend:
                trends = trend[1][0]
                trendi = trend[1][1]
                predicted_price = self.price_prediction(timeframe, trends, trendi)
                if price < predicted_price: sellConfidence += 1
            shouldSell = sellConfidence == len(mintrend)

        if maxtrend:
            buyConfidence = 0
            price = buydata[timeframe]
            for trend in mintrend:
                trends = trend[1][0]
                trendi = trend[1][1]
                predicted_price = self.price_prediction(timeframe, trends, trendi)
                if price > predicted_price: buyConfidence += 1
            shouldBuy = buyConfidence == len(maxtrend)

        return [shouldSell, shouldBuy]


    def price_prediction(self, time, slope, intercept):
        return time * slope + intercept


def download_data(tickers):
    filenames = []
    for ticker in tickers:
        filename = '{0}.csv'.format(ticker)
        yf.download(tickers=ticker, period="7d", interval="1m").to_csv(filename)
        data = pd.read_csv(filename, sep=r'\s*,\s*', header=0, encoding='ascii', engine='python')
        data['Datetime'] = data['Datetime'].apply(lambda x: str(x)[0:19])
        data.to_csv(filename, sep=',', header=0, encoding='ascii')
        filenames.append(filename)
    return filenames
def parse_data(filenames):
    datas = []
    for filename in filenames:
        datas.append(bt.feeds.GenericCSVData(
            dataname=filename,
            dtformat=('%Y-%m-%d %H:%M:%S'),
            timeframe=bt.TimeFrame.Minutes,
            datetime=1,
            open=2,
            high=3,
            low=4,
            close=5,
            volume=7))
    return datas

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    strats = cerebro.addstrategy(Strategy)

    filenames = download_data(['AAPL', 'FB', 'MSFT', 'GOOG', 'TSLA', '^GSPC', 'AMZN',
                               'V', 'JNJ', 'WMT', 'JPM', 'PG', 'MA', 'DIS', 'IBM',
                               'NVDA', 'BMY', 'CRM', 'PYPL', 'KO', 'DO', 'INTC'])
    datas = parse_data(filenames)

    for data in datas: cerebro.adddata(data)

    cerebro.run()
    cerebro.plot()
