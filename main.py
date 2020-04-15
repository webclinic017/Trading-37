from __future__ import (absolute_import,
                        division,
                        print_function,
                        unicode_literals)

import yfinance as yf

import trendln as tl

import backtrader as bt

class Strategy(bt.Strategy):
    params = (
        ('timeframe', 60),
        ('printlog', True)
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt, txt))

    def next(self):
        if len(self) < self.params.timeframe: return

        for dataindex, data in enumerate(self.datas):
            hasOrder = False
            for order in self.broker.get_orders_open():
                if order.data == data: hasOrder = True
            if hasOrder: continue

            dataArray = []
            for i in range(-self.params.timeframe, 0):
                dataArray.append(data.close[i])

            (_, pmin, mintrend, _), (_, pmax, maxtrend, _) = tl.calc_support_resistance(dataArray)

            if maxtrend or mintrend:
                position = self.getposition(data=data, broker=self.broker)

                shouldBuy = False
                if maxtrend:
                    if position: break

                    calculatedShouldBuy = True
                    for max in maxtrend:
                        maxs = max[1][0]
                        maxi = max[1][1]
                        maxprediction = self.params.timeframe * maxs + maxi
                        if data.close[0] < maxprediction: calculatedShouldBuy = False

                    shouldBuy = calculatedShouldBuy

                shouldSell = False
                if mintrend:
                    if not position: break

                    calculatedShouldSell = True
                    for min in mintrend:
                        mins = min[1][0]
                        mini = min[1][1]
                        minprediction = self.params.timeframe * mins + mini
                        if data.close[0] > minprediction: calculatedShouldSell = False

                    shouldSell = calculatedShouldSell

                if shouldBuy and shouldSell: break

                if shouldSell:
                    self.sell(data=data, size=position.size)
                    self.log('Sold data #{0} for {1}'.format(dataindex, data.close[0]))
                elif shouldBuy:
                    self.buy(data=data, size=1)
                    self.log('Bought data #{0} for {1}'.format(dataindex, data.close[0]))

    def notify_trade(self, trade):
        if not trade.isclosed: return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def start(self):
        self.log('Start cash: %.2f' %
                 (self.broker.getvalue()), doprint=True)
    def stop(self):
        self.log('End cash: %.2f' %
                 (self.broker.getvalue()), doprint=True)

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    # Add a strategy
    strats = cerebro.addstrategy(Strategy)

    yf.download(tickers="AAPL", period="max", interval="1d").to_csv('data.csv')
    data = bt.feeds.YahooFinanceCSVData(dataname='data.csv')

    cerebro.adddata(data)

    cerebro.run()
    cerebro.plot()