#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015, 2016 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,)
#                        unicode_literals)

import trendln as tl
import backtrader as bt

class St(bt.Strategy):
    params = (
        ('timeframe', 60),
        ('printlog', True)
    )

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
                    self.log(data, 'Sold data #{0} for {1}'.format(dataindex, data.close[0]))
                elif shouldBuy:
                    self.buy(data=data, size=1)
                    self.log(data, 'Bought data #{0} for {1}'.format(dataindex, data.close[0]))

    def notify_trade(self, trade):
        if not trade.isclosed: return
        self.log(trade.data, 'OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def start(self):
        print('Start cash: %.2f' % (self.broker.getvalue()))

    def stop(self):
        print('End cash: %.2f' % (self.broker.getvalue()))

if __name__ == '__main__':

    data = bt.feeds.BacktraderCSVData(dataname='min_data.txt',timeframe=bt.TimeFrame.Minutes)

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(St)

    cerebro.broker.setcash(10000.0)

    cerebro.run()