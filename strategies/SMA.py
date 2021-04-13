import backtrader as bt
import math

class PandasSMA(bt.feeds.PandasData):
    lines = ('close','sma30','sma100','buy_signal','sell_signal')
    params = (
        ('datetime', None),
        ('open',5),
        ('high',None),
        ('low',None),
        ('close',0),
        ('volume',None),
        ('openinterest',None),
        ('adj_close',None),
        ('sma30', 1),
        ('sma100', 2),
        ('buy_signal', 3),
        ('sell_signal',4)
    )

class TestSMA(bt.Strategy):
    def __init__(self):
        self.sell_signal = self.datas[0].sell_signal
        self.buy_signal = self.datas[0].buy_signal

    def next(self):
        if not(math.isnan(self.buy_signal[0])):
            self.buy()
            print('buy at',self.buy_signal[0])
        elif not(math.isnan(self.sell_signal[0])):
            self.sell()
            print('sell at',self.sell_signal[0])


