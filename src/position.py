from enum import Enum

try:
    from my.sdp.api import (Direction, OpenClose, OrderStatus, Exchange)
except ImportError:
    pass

"""Constants
"""
LONG_OPEN = 0
LONG_CLOSE = 1
SHORT_OPEN = 2
SHORT_CLOSE = 3

ERROR_CODE = -1

class PosMgrBase(object):
    """A base class providing position management

    Attributes
    ----------
    position : dict
        symbol: str i.e. 'm1701'
            index: {LONG_OPEN, LONG_CLOSE, SHORT_OPEN, SHORT_CLOSE)
                {
                    'pos'
                    'notional'
                    'yes_pos'
                    'yes_notional'
                }
    contract_info : contract
        stores contract from config
    """

    def __init__(self):
        self.position = {}
        self.account = {}
        self.contract_info = {}
        self.account_info = {}
        self.orders = {}
        self.prices = {}
        self.CLOSE_YES_FIRST = True

    @staticmethod
    def switch_side(direction):
        return Direction.BUY.value if direction == Direction.SELL.value else Direction.SELL.value

    @staticmethod
    def direction_to_index(direction, openclose):
        """

        Parameters
        ----------
        direction : int or Direction
        openclose : int or OpenClose

        Returns
        -------
        index : {LONG_OPEN, LONG_CLOSE, SHORT_OPEN, SHORT_CLOSE}
            index within position dict

        """
        _INDEX_MAP = {
            Direction.BUY.value: {
                OpenClose.OPEN.value: LONG_OPEN, 
                OpenClose.CLOSE.value: LONG_CLOSE,
                OpenClose.CLOSE_TOD.value: LONG_CLOSE,
                OpenClose.CLOSE_YES.value: LONG_CLOSE
                },
            Direction.SELL.value: {
                OpenClose.OPEN.value: SHORT_OPEN,
                OpenClose.CLOSE.value: SHORT_CLOSE,
                OpenClose.CLOSE_TOD.value: SHORT_CLOSE,
                OpenClose.CLOSE_YES.value: SHORT_CLOSE
            }
        }
        _direction = direction.value if isinstance(direction, Enum) else direction
        _open_close = openclose.value if isinstance(openclose, Enum) else openclose
        return _INDEX_MAP[_direction][_open_close]

    @staticmethod
    def get_transaction_fee(contract, size, price, flag_close_yes=False):
        """get transaction fee for current transaction

        Parameters
        ----------
        contract : contract
        size : int
        price : float
        flag_close_yes : bool

        Returns
        -------
        fee : float

        """
        if flag_close_yes:
            exchange_fee = contract.fee['yes_exchange_fee']
        else:
            exchange_fee = contract.fee['exchange_fee']
        if contract.fee['fee_by_lot'] == 0:
            fee = size * (exchange_fee + contract.fee['broker_fee'])  # Caution, for futures right now, broker fee is 0.0
        else:
            fee = size * price * (exchange_fee + contract.fee['broker_fee'])
        if contract.exch == Exchange.SSE.short_name:
            fee += size * price * contract.fee['acc_transfer_fee']
        return fee

    def get_symbol_position_detail(self, symbol):
        """position of given symbol

        Parameters
        ----------
        symbol : str

        Returns
        -------
        position : list
            0 for long open, 1 for long close, 2 for short open, 3 for short close

        """
        return self.position[symbol]

    def get_long_position(self, symbol):
        """long position of contract

        Parameters
        ----------
        symbol : str
            i.e. 'i1801'

        Returns
        -------
        position : int

        """
        return self.position[symbol][LONG_OPEN]['pos'] - self.position[symbol][SHORT_CLOSE]['pos']

    def get_short_position(self, symbol):
        """short position of contract

        Parameters
        ----------
        symbol

        Returns
        -------
        position : int

        """
        return self.position[symbol][SHORT_OPEN]['pos'] - self.position[symbol][LONG_CLOSE]['pos']

    def get_net_position(self, symbol):
        """net position: LONG - SHORT

        Parameters
        ----------
        symbol

        Returns
        -------
        position : int
            net position of difference between LONG and SHORT

        """
        return self.get_long_position(symbol) - self.get_short_position(symbol)

    def get_yes_position(self, symbol):
        """

        Parameters
        ----------
        symbol

        Returns
        -------
        yesterday position : dict
            ::
                {
                    "long": {"pos", "notional"},
                    "short": {"pos", "notional"}
                }

        """
        return {
            'long': {
                'pos': self.position[symbol][LONG_OPEN]['yes_pos'],
                'notional': self.position[symbol][LONG_OPEN]['yes_notional']
            },
            'short': {
                'pos': self.position[symbol][SHORT_OPEN]['yes_pos'],
                'notional': self.position[symbol][SHORT_OPEN]['yes_notional']
            }
        }

    def get_avg_position_price(self, symbol, direction):
        """calculate average price for current long or short position

        Parameters
        ----------
        symbol : str
        direction : int

        Returns
        -------
        price : float or -1
            -1 for error, otherwise average price

        """
        if direction == Direction.BUY.value:
            long_position = self.get_long_position(symbol)
            if long_position > 0:
                return (self.position[symbol][LONG_OPEN]['notional'] - self.position[symbol][SHORT_CLOSE]['notional']) / \
                       long_position
            elif long_position == 0:
                return 0.0
            else:
                print ("long position is less than 0")
                return ERROR_CODE
        else:
            short_position = self.get_short_position(symbol)
            if short_position > 0:
                return (self.position[symbol][SHORT_OPEN]['notional'] - self.position[symbol][LONG_CLOSE]['notional']) / \
                       short_position
            elif short_position == 0:
                return 0.0
            else:
                print ("short position is less than 0")
                return ERROR_CODE

    def get_sell_open_avg_px(self, symbol):
        """calculate average sell open price

        Parameters
        ----------
        symbol : str

        Returns
        -------
        price : float or -1
            -1 for error, otherwise average price

        """
        short_open_position = self.position[symbol][SHORT_OPEN]['pos']
        if  short_open_position < 0:
            print ("position is less than zero")
            return ERROR_CODE
        elif short_open_position == 0:
            return 0.0
        else:
            return self.position[symbol][SHORT_OPEN]['notional'] / short_open_position

    def get_buy_open_avg_px(self, symbol):
        """calculate average buy open price

        Parameters
        ----------
        symbol : str

        Returns
        -------
        price : float or -1
            -1 for error, otherwise average price

        """
        long_open_position = self.position[symbol][LONG_OPEN]['pos']
        if long_open_position < 0:
            print ("position is less than zero")
            return ERROR_CODE
        elif long_open_position == 0:
            return 0.0
        else:
            return self.position[symbol][LONG_OPEN]['notional'] / long_open_position

    def init_position(self, config_type, config):
        """initialize start position

        Parameters
        ----------
        config_type : int
            type of config
        config : :obj:config
            strategy configuration

        Returns
        -------
        None

        """
        for contract in config.contracts:
            self.contract_info[contract.symbol] = contract
            self.position[contract.symbol] = [{
                'yes_pos': 0,
                'yes_notional': 0.0,
                'pos': 0,
                'notional': 0.0
                } for i in range(4)]

            self.position[contract.symbol][LONG_OPEN] = {
                'yes_pos':  contract.yesterday_pos['long_volume'],
                'yes_notional': contract.yesterday_pos['long_volume'] * contract.yesterday_pos['long_price'],
                'pos': contract.today_pos['long_volume'],
                'notional': contract.today_pos['long_volume'] * contract.today_pos['long_price']
            }
            self.position[contract.symbol][SHORT_OPEN] = {
                'yes_pos':  contract.yesterday_pos['short_volume'],
                'yes_notional': contract.yesterday_pos['short_volume'] * contract.yesterday_pos['short_price'],
                'pos': contract.today_pos['short_volume'],
                'notional': contract.today_pos['short_volume'] * contract.today_pos['short_price']
            }
            self.prices[contract.symbol] = {
                "last_px": 0.0
            }
        for account in config.accounts:
            self.account_info[account.account] = account
            self.account[account.account] = {
                "cash_available":  account.cash_available,
                "cash_asset": account.cash_asset
            }

    def update_position(self, response_type, response):
        """update position on each response

        Parameters
        ----------
        response_type : int
            type of response
        response : :obj:response
            response from exchange

        Returns
        -------
        None

        """
        # calculate pos
        if response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value):
            if response.exe_volume == 0:
                return
            # fee calculation
            contract = self.contract_info[response.symbol]
            fees = self.get_transaction_fee(contract, response.exe_volume, response.exe_price)
            close_fees = 0
            if response.open_close == OpenClose.CLOSE_YES.value:
                close_fees -= fees  # If it's close yesterday, revert back using today's fee.
                # Add two yesterday fee back.
                close_fees += (2 * self.get_transaction_fee(contract, response.exe_volume, response.exe_price, True))
            else:
                close_fees = fees
            # notional calculation
            notional_change = response.exe_volume * response.exe_price
            # update yesterday pos, not accounting for fees
            opposite_index = self.direction_to_index(self.switch_side(response.direction), OpenClose.OPEN)
            if response.open_close == OpenClose.CLOSE_YES:
                self.position[response.symbol][opposite_index]['yes_pos'] -= response.exe_volume
                self.position[response.symbol][opposite_index]['yes_notional'] -= notional_change
            elif response.open_close == OpenClose.CLOSE and self.CLOSE_YES_FIRST:
                opposite_yes_pos = self.position[response.symbol][opposite_index]['yes_pos']
                pos_diff = opposite_yes_pos - response.exe_volume
                if pos_diff > 0:
                    self.position[response.symbol][opposite_index]['yes_pos'] -= response.exe_volume
                    self.position[response.symbol][opposite_index]['yes_notional'] -= notional_change
                else:
                    self.position[response.symbol][opposite_index]['yes_pos'] = 0
                    self.position[response.symbol][opposite_index]['yes_notional'] = 0.0
            # update today pos, accounting fees as cost for position
            _index = self.direction_to_index(response.direction, response.open_close)
            if response.direction == Direction.BUY.value:
                if response.open_close == OpenClose.OPEN.value:
                    self.position[response.symbol][_index]['notional'] += (notional_change + fees)
                    self.position[response.symbol][_index]['pos'] += response.exe_volume
                elif response.open_close in (OpenClose.CLOSE.value, OpenClose.CLOSE_YES.value):
                    self.position[response.symbol][_index]['notional'] += (notional_change + close_fees)
                    self.position[response.symbol][_index]['pos'] += response.exe_volume
            elif response.direction == Direction.SELL.value:
                fees += notional_change * contract.fee['stamp_tax']
                if response.open_close == OpenClose.OPEN.value:
                    self.position[response.symbol][_index]['notional'] += (notional_change - fees)
                    self.position[response.symbol][_index]['pos'] += response.exe_volume
                elif response.open_close in (OpenClose.CLOSE.value, OpenClose.CLOSE_YES.value):
                    self.position[response.symbol][_index]['notional'] += (notional_change - close_fees)
                    self.position[response.symbol][_index]['pos'] += response.exe_volume

    def update_cash_on_order(self, order):
        """
        When opening positions, we update cash upon sending order for compliance.

        Parameters
        ----------
        order : object

        Returns
        -------

        """
        # TODO : verify logic, not available yet
        self.orders[order.order_id] = order

        contract = self.contract_info[order.symbol]
        if order.status == OrderStatus.INIT.value:  # New Order
            if order.exch in (Exchange.SZSE.short_name, Exchange.SSE.short_name):  # stocks
                stock_value = order.price * order.size
                transaction_fee = self.get_transaction_fee(contract, order.size, order.price)
                total_fees = stock_value * contract['stamp_tax'] + transaction_fee

                if order.direction == Direction.BUY.value:
                    self.account[contract.account]['cash_available'] -= stock_value
                else:
                    self.account[contract.account]['cash_available'] -= total_fees
            else: # futures
                futures_value = order.price * order.size * contract['multiplier']
                transaction_fee = self.get_transaction_fee(contract, order.size, order.price) * contract['multiplier']
                if order.open_close == OpenClose.OPEN.value:
                    self.account[contract.account]['cash_available'] -= (futures_value + transaction_fee)

    def update_cash_on_response(self, response_type, response):
        """
        When closing positions, we update cash records at a later stage after we receive actual response. Previously
        deducted cash might be added back to reflect closed positions or cancelled operations.

        Parameters
        ----------
        response_type
        response

        Returns
        -------

        """
        # TODO : verify logic, not available yet
        contract = self.contract_info[response.symbol]
        order = self.orders[response.order_id]
        if response.status in (OrderStatus.CANCELED.value, OrderStatus.REJECTED.value):  # Cancel or rejected
            # revert back positions and available cash
            if contract.exch in (Exchange.SZSE.short_name, Exchange.SSE.short_name):  # Stocks, multiplier is 1
                stock_value = order.price * order.size
                transaction_fee = self.get_transaction_fee(contract, order.size, order.price)
                fees = stock_value * contract['stamp_tax'] + transaction_fee
                if order.direction == Direction.BUY.value:
                    self.account[contract.account]['cash_available'] += stock_value
                else:
                    self.account[contract.account]['cash_available'] += fees
            else: # futures
                futures_value = order.price * order.size * contract['multiplier']
                transaction_fee = self.get_transaction_fee(contract, order.size, order.price) * contract['multiplier']
                if order.open_close == OpenClose.OPEN.value:
                    self.account[contract.account]['cash_available'] += (futures_value + transaction_fee)

        elif response.status in (OrderStatus.SUCCEED.value, OrderStatus.PARTED.value):
            # Add cash upon part/success sell response
            if contract.exch in (Exchange.SZSE.short_name, Exchange.SSE.short_name):  # Stocks, multiplier is 1
                stock_value = order.last_px * order.last_qty
                if order.direction == Direction.SELL.value:
                    self.account[contract.account]['cash_available'] += stock_value
            elif order.open_close in (OpenClose.CLOSE.value, OpenClose.CLOSE_YES.value):
                # When close a position, we reset the cash.
                # When a position is closed, it  will release some cash for openning that account
                futures_value = order.last_px * order.last_qty * contract['multiplier']
                if order.direction == Direction.BUY.value:
                    sell_open_avg_px = self.get_sell_open_avg_px(order.symbol)
                    self.account[contract.account]['cash_available'] += \
                        (sell_open_avg_px + (sell_open_avg_px - order.last_px)) * order.last_qty * contract['multiplier']
                elif order.direction == Direction.SELL.value:
                    self.account[contract.account]['cash_available'] += futures_value
            elif order.open_close == OpenClose.OPEN.value:
                price_gap = order.price - order.last_px  # If we send a price higher than last_px, we need to re-adjust the gap to cash.
                self.account[contract.account]['cash_available'] += price_gap * order.last_qty * contract['multiplier']

    def update_last_px(self, quote_type, quote):
        """update last price of contract
        ``required for pnl calculation``

        Parameters
        ----------
        quote_type : int
            type of quote
        quote : object
            quote object

        Returns
        -------
        None

        """
        if quote_type == 0:
            self.prices[quote.symbol]["last_px"] = quote.last_px
        elif quote_type == 1:
            self.prices[quote.ticker]["last_px"] = quote.last_px


    @staticmethod
    def avg_px(pos_info):
        """average price of position

        Parameters
        ----------
        pos_info : dict
            ::

                {"notional": , "pos": }

        Returns
        -------
        price : float

        """
        if pos_info['pos'] > 0:
            return pos_info['notional'] / pos_info['pos']
        else:
            return 0

    def get_realized_pnl(self, symbol):
        """calculate realized pnl by points
        (need to multiply contract multiple in order to get cash pnl)
        Realized pnl meaning position that has been closed.

        Parameters
        ----------
        symbol : str

        Returns
        -------
        pnl : float
            by points

        """
        _position = self.position[symbol]
        long_pos = min(_position[LONG_OPEN]['pos'], _position[SHORT_CLOSE]['pos'])
        short_pos = min(_position[SHORT_OPEN]['pos'], _position[LONG_CLOSE]['pos'])

        long_side_pnl = long_pos * (self.avg_px(_position[SHORT_CLOSE]) - self.avg_px(_position[LONG_OPEN]))
        short_side_pnl = short_pos * (self.avg_px(_position[SHORT_OPEN]) - self.avg_px(_position[LONG_CLOSE]))

        return long_side_pnl + short_side_pnl
    
    def get_unrealized_pnl(self, symbol):
        """calculate unrealized pnl by points
        (need to multiply contract multiple in order to get cash pnl)
        Unrealized pnl meaning pnl of holding positions based on last price of quote.

        Parameters
        ----------
        symbol : str

        Returns
        -------
        pnl : float
            by points

        """
        position = self.position[symbol]
        long_pos = self.get_long_position(symbol)
        short_pos = self.get_short_position(symbol)
        last_px = self.prices[symbol]['last_px']

        if last_px - 0 < 0.01:
            return 0

        if long_pos >= 0:
            long_side_unrealized_pnl = long_pos * (last_px - self.avg_px(position[LONG_OPEN]))

        if short_pos >= 0:
            short_side_unrealized_pnl = short_pos * (self.avg_px(position[SHORT_OPEN]) - last_px)

        return long_side_unrealized_pnl + short_side_unrealized_pnl

    def get_contract_pnl_cash(self, symbol):
        """get total contract pnl by cash

        Parameters
        ----------
        symbol : str

        Returns
        -------
        pnl : float
            by cash

        """
        contract = self.contract_info[symbol]
        account = self.account_info[contract.account]
        return (self.get_realized_pnl(symbol) + self.get_unrealized_pnl(symbol)) * contract.multiple * account.exch_rate

    def get_strategy_pnl_cash(self):
        """get strategy pnl by cash

        Returns
        -------
        pnl : float
            by cash

        """
        _pnl = 0
        for symbol, contract in self.contract_info.items():
            _pnl += self.get_contract_pnl_cash(symbol)
        return _pnl
