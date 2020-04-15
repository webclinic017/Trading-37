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

            (_, c_pmin, c_mintrend, _), (_, c_pmax, c_maxtrend, _) = tl.calc_support_resistance(closedata[:-1])
            (_, lh_pmin, lh_mintrend, _), (_, lh_pmax, lh_maxtrend, _) = tl.calc_support_resistance((lowdata[:-1], highdata[:-1]))

            c_buy_sell_prediction = self.buy_sell_prediction(closedata,
                                                             self.params.timeframe,
                                                             c_pmin, c_mintrend,
                                                             c_pmax, c_maxtrend)
            hl_buy_sell_prediction = self.buy_sell_prediction(closedata,
                                                              self.params.timeframe,
                                                              lh_pmin, lh_mintrend,
                                                              lh_pmax, lh_maxtrend)

            buyConfidence = max(c_buy_sell_prediction[0], hl_buy_sell_prediction[0])
            sellConfidence = max(c_buy_sell_prediction[1], hl_buy_sell_prediction[1])

            if buyConfidence <= 1 and sellConfidence <= 1: continue

            position = self.broker.getposition(data=data)
            if buyConfidence > sellConfidence:
                if not position:
                    self.buy(data=data, size=10)
                    self.log(data, 'Bought data #{0} for {1}'.format(dataindex, closedata[0]))
            elif sellConfidence > buyConfidence:
                if position:
                    self.sell(data=data, size=position.size)
                    self.log(data, 'Sold data #{0} for {1}'.format(dataindex, closedata[0]))

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

    def buy_sell_prediction(self, dataclose, timeframe, pmin, mintrend, pmax, maxtrend):
        buyConfidence = 0
        sellConfidence = 0

        if maxtrend:
            for max in maxtrend:
                maxs = max[1][0]
                maxi = max[1][1]
                if dataclose[0] > self.price_prediction(timeframe, maxs, maxi):
                    buyConfidence += 1
                else:
                    buyConfidence -= 1

        if mintrend:
            for min in mintrend:
                mins = min[1][0]
                mini = min[1][1]
                if dataclose[0] < self.price_prediction(timeframe, mins, mini):
                    sellConfidence += 1
                else:
                    sellConfidence -= 1

        if buyConfidence == sellConfidence:
            if pmax:
                maxs = pmax[0]
                maxi = pmax[1]
                if dataclose[0] > self.price_prediction(timeframe, maxs, maxi):
                    buyConfidence += 1
                else:
                    buyConfidence -= 1

            if pmin:
                mins = pmin[0]
                mini = pmin[1]
                if dataclose[0] < self.price_prediction(timeframe, mins, mini):
                    sellConfidence += 1
                else:
                    sellConfidence -= 1

        return [buyConfidence, sellConfidence]

    def price_prediction(self, time, slope, intercept):
        return time * slope + intercept


def download_data():
    yf.download(tickers="AAPL", period="7d", interval="1m").to_csv('data.csv')
    data = pd.read_csv('data.csv', sep=r'\s*,\s*', header=0, encoding='ascii', engine='python')
    data['Datetime'] = data['Datetime'].apply(lambda x: str(x)[0:19])
    data.to_csv('data.csv', sep=',', header=0, encoding='ascii')
def parse_data():
    return bt.feeds.GenericCSVData(
            dataname='data.csv',
            dtformat=('%Y-%m-%d %H:%M:%S'),
            timeframe=bt.TimeFrame.Minutes,
            datetime=1,
            open=2,
            high=3,
            low=4,
            close=5,
            volume=7)

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    strats = cerebro.addstrategy(Strategy)

    download_data()
    data = parse_data()

    cerebro.adddata(data)

    cerebro.run()
    cerebro.plot()