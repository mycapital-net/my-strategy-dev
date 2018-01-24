"""A template class to construct bar quote
"""

class InternalBar(object):
    """structure to store each bar quote

    Attributes
    ----------
    symbol : str
        i.e. 'a1801'
    int_time : int
        i.e. 90005000
    open : float
    close : float
    high : float
    low : float
    volume : int
    turnover : float
    upper_limit : float
    lower_limit : float
    open_interest : float
    bar_index : int
        counts up from 0 for each session
    """
    def __init__(self):
        self.symbol = ''
        self.int_time = 0
        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.volume = 0  # Total shares/vol
        self.turnover = 0  # Total Traded Notional
        self.upper_limit = 0
        self.lower_limit = 0
        self.open_interest = 0
        self.bar_index = 0

    def clear(self):
        self.symbol = ''
        self.int_time = 0
        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.volume = 0  # Total shares/vol
        self.turnover = 0  # Total Traded Notional
        self.upper_limit = 0
        self.lower_limit = 0
        self.open_interest = 0
        self.bar_index = 0


class BarStruct(object):
    """stores additional information on bar construction

    Attributes
    ----------
    bar_index : int
    last_bar_time : int
        int time of last bar converted to minutes
    open_vol : int
        total volume of last bar to compute difference
    open_notional : float
        similar to open_vol, total notional of last bar
    cur_bar : InternalBar
        stores current bar

    """
    def __init__(self):
        self.bar_index = 0
        self.last_bar_time = 0
        self.open_vol = 0
        self.open_notional = 0
        self.cur_bar = None


class BarGenerator(object):
    MI_DCE_ORDER_STATISTIC = 3
    def __init__(self, bar_interval):
        self.bar_interval = bar_interval
        self.bar_struct_map = {}

    @staticmethod
    def int_time_to_min(int_time):
        hour2min = (int_time // 10000000) * 60
        minutes = (int_time % 10000000) // 100000
        return hour2min + minutes

    def process_bar_data(self, context, quote_type, quote, on_book):
        """generate bar from tick data, should be called at on_book interface

        Parameters
        ----------
        context : object
            context class for passing variables across function
        quote_type : {0, 1}
            0 for futures, 1 for stock
        quote : object
            current tick quote object
        on_book : object
            call back function, should be on book

        Returns
        -------

        """
        if quote_type == 3:
            return
        if quote_type == 0 and quote.feed_type == self.MI_DCE_ORDER_STATISTIC:
            return

        symbol = quote.symbol if quote_type == 0 else quote.ticker
        int_time = quote.int_time if quote_type == 0 else quote.exch_time

        # first tick new bar
        if symbol not in self.bar_struct_map:
            bar_item = BarStruct()
            bar_quote = InternalBar()
            bar_quote.symbol = symbol
            bar_quote.int_time = int_time // 100000 * 100000
            bar_quote.open = quote.last_px
            bar_quote.high = quote.last_px
            bar_quote.low = quote.last_px
            bar_quote.upper_limit = quote.upper_limit_px
            bar_quote.lower_limit = quote.lower_limit_px
            # store bar open information
            bar_item.bar_index = 0
            bar_item.last_bar_time = self.int_time_to_min(int_time)
            bar_item.open_vol = quote.total_vol
            bar_item.open_notional = quote.total_notional
            bar_item.cur_bar = bar_quote

            self.bar_struct_map[symbol] = bar_item
        else:
            bar_item = self.bar_struct_map[symbol]
            bar_quote = bar_item.cur_bar
            bar_quote.symbol = symbol

            if bar_quote.int_time == 0:
                bar_quote.open = quote.last_px
                bar_quote.high = quote.last_px
                bar_quote.low = quote.last_px
                bar_quote.upper_limit = quote.upper_limit_px
                bar_quote.lower_limit = quote.lower_limit_px
                # store bar open information
                bar_item.open_vol = quote.total_vol
                bar_item.open_notional = quote.total_notional
            else:
                # update high and low prices
                if quote.last_px > bar_quote.high:
                    bar_quote.high = quote.last_px
                if quote.last_px < bar_quote.low:
                    bar_quote.low = quote.last_px

            # update int_time each tick
            bar_quote.int_time = int_time // 100000 * 100000
            cur_time = self.int_time_to_min(int_time)
            if cur_time - bar_item.last_bar_time >= self.bar_interval:
                bar_quote.close = quote.last_px
                bar_quote.open_interest = quote.open_interest
                bar_quote.turnover = quote.total_notional - bar_item.open_notional
                bar_quote.volume = quote.total_vol - bar_item.open_vol
                bar_quote.bar_index = bar_item.bar_index
                on_book(context, 3, bar_quote)
                bar_quote.clear()
                bar_item.last_bar_time = cur_time
                bar_item.bar_index += 1
