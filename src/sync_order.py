# encoding: utf-8
"""This is a Synchronous order interface which should replace the original 
`Order` and `Logger` classes provided by the API document.

In order for it to function correctly, the following interface should be called
appropriately within strategy source:

1. SyncOrder.__init__
    Construction and initialization of the class. Should be called at "on_init" of <strategy name>.py
2. SyncOrder.on_response
    Update position and order information. Should be called at "on_response" of <strategy name>.py

The following functions are provided:
1. SyncOrder.delayed_orders, SyncOrder.active_orders
    property containning information on pending orders, namely buffered and sent but not finished.
2. SyncOrder.info
    replace Logger.info
3. SyncOrder.clear_delayed_orders
    clear delayed order for given symbol
4. SyncOrder.cancelling
    return true if there is pending cancel on given symbol
5. SyncOrder.send_single_order, SyncOrder.cancel_single_order
    A wrapped synchronous send/cancel order interface. 
    Should replace `Order.send_single_order`/`Order.cancel_single_order`.
    If there is pending cancel, orders will be buffered. Once cancel is finished, the buffered orders will
    be sent.
"""
from my.sdp.api import Order, Logger, OrderStatus, Direction, OpenClose
from enum import IntEnum

class SyncOrderRet(IntEnum):
    ORDER_NOT_FOUND = -1001

class SyncOrder(Order, Logger):
    def __init__(self, context, config):
        super(SyncOrder, self).__init__(context, config)
        self.debug = True
        if self.debug:
            self.info = self.log_debug
        else:
            self.info = self.nil
        self._active_orders = {}
        self._delayed_orders = {}

    @staticmethod
    def nil(*args, **kwargs):
        return

    def log_debug(self, contents):
        """logging with time info, need to acquire time by calling on book
        """
        print("[{}] {}".format("SyncOrder", contents))
        Logger.info(self, "[{}] {}".format("SyncOrder", contents))

    @property
    def delayed_orders(self):
        return self._delayed_orders

    def _delay_order(self, symbol, price, size, direction, open_close, *args, **kwargs):
        """record delay order"""
        delay_list = self._delayed_orders.setdefault(symbol, [])
        delay_list.append({
            "symbol": symbol, "price": price, "size": size, "direction": direction,
            "open_close": open_close, "kwargs": kwargs,
        })
        self.info("Delay order: {} {} {} {} @ {}".format(
            symbol, Direction(direction).name, OpenClose(open_close).name, size, price
        ))

    @property
    def active_orders(self):
        return self._active_orders

    def _record_order(self, order_id, symbol, price, size, direction, open_close, *args, **kwargs):
        """record sending single order"""
        self._active_orders[order_id] = {
            "order_id": order_id, "symbol": symbol, "price": price, "size": size,
            "direction": direction, "open_close": open_close,
            # kwargs
            "investor_type": kwargs.get("investor_type"), "order_type": kwargs.get("order_type"),
            "time_in_force": kwargs.get("time_in_force"),
            # additional fields
            "pending_cancel": False, "cum_amount": 0.0, "cum_qty": 0, "last_px": 0.0,
            "last_qty": 0, "status": OrderStatus.INIT.value
        }

    def cancelling(self, symbol):
        """check if is cancelling orders of given symbol"""
        if any([order['pending_cancel'] for order in self._active_orders.values() if order['symbol'] == symbol]):
            return True
        else:
            return False

    def clear_delayed_orders(self, symbol=None):
        """Clear delayed orders

        Parameters
        ----------
        symbol: str (Optional)
            cancel previous buffered orders

        Returns
        -------
        None

        """
        if symbol:
            if symbol in self.delayed_orders:
                self._delayed_orders.pop(symbol)
        else:
            self._delayed_orders = {}

    def on_response(self, response_type, response):
        """includes following functions:
        1. logging responses.
        2. update order status
        """
        self.info("Order Resp: {} {} {} {} {} @ {} {} {} {}".format(
            response.order_id, response.symbol, Direction(response.direction).name,
            OpenClose(response.open_close).name, response.exe_volume, response.exe_price,
            OrderStatus(response.status).name, response.error_no, response.error_info
        ))
        # finish order with succeed/canceled/rejected/interrejected
        if (response.status == OrderStatus.SUCCEED.value and response.exe_volume > 0) or response.status in (
                OrderStatus.CANCELED.value, OrderStatus.REJECTED.value, OrderStatus.INTERREJECTED.value):
            if response.order_id in self._active_orders:
                self._active_orders.pop(response.order_id)
        # update order according to response
        else:
            if response.order_id in self._active_orders:
                order = self._active_orders[response.order_id]
                if response.status == OrderStatus.PARTED.value and response.exe_volume > 0:
                    # volume filled needs update
                    order["cum_amount"] += response.exe_volume * response.exe_price
                    order["cum_qty"] += response.exe_volume
                    order["last_px"] = response.exe_price
                    order["last_qty"] = response.exe_volume
                elif response.status == OrderStatus.CANCEL_REJECTED.value:
                    # remove pending cancel
                    if order["pending_cancel"]:
                        order["pending_cancel"] = False
                order["status"] = response.status
                self._active_orders[response.order_id] = order
        if not self.cancelling(response.symbol):
            if response.symbol in self._delayed_orders:
                for o in self._delayed_orders[response.symbol]:
                    self.send_single_order(
                        o["symbol"], o["price"], o["size"], o["direction"], o["open_close"],
                        kwargs=o["kwargs"]
                    )
                self.clear_delayed_orders(response.symbol)

    def send_single_order(self, symbol, price, size, direction, open_close, *args, **kwargs):
        """ send single order synchronously with logging and order management """
        if size == 0:
            return 0
        elif self.cancelling(symbol):
            self._delay_order(symbol, price, size, direction, open_close, args, kwargs)
            return 0
        order_id = Order.send_single_order(self, symbol, price, size, direction, open_close, kwargs=kwargs)
        self.info("Send order: {} {} {} {} {} @ {}".format(
            order_id, symbol, Direction(direction).name, OpenClose(open_close).name, size, price)
        )
        if order_id > 0:
            self._record_order(order_id, symbol, price, size, direction, open_close, kwargs=kwargs)
        return order_id

    def _record_cancel(self, order_id):
        """ record cancelling single order """
        if not self._active_orders[order_id]["pending_cancel"]:
            self._active_orders[order_id]["pending_cancel"] = True

    def cancel_single_order(self, order_id):
        """ cancel single order and recording cancel """
        ret = 0
        if order_id not in self._active_orders:
            self.info("Cancel order: {}, ret: {}".format(order_id, SyncOrderRet.ORDER_NOT_FOUND.name))
            return SyncOrderRet.ORDER_NOT_FOUND
        if not self._active_orders[order_id]["pending_cancel"]:
            ret = Order.cancel_single_order(self, order_id)
            self.info("Cancel order: {}, ret: {}".format(order_id, ret))
            if ret == 0:
                self._record_cancel(order_id)
        return ret