此模块提供基本的订单管理功能，由 OrdMgr 类实现。
- 订单管理功能
    - 初始化时创建一个 `OrdMgr` 的实例
    - 发单时调用`send_order()`接口记录订单、
    - 撤单时调用`cancel_order()`接口记录撤单
    - 收到回报时需要调用`on_response()`接口根据回报更新订单状态
---------
####查询接口

|	属性	|	描述	|	类型	|	返回	|
|	:------------	|	:------------	|	:------------	|	:------------		|
|active_orders|目前的存活订单|dict|返回目前的存活订单，以order_id为key|
注：存活订单指未被撤单、未被拒绝且未完全成交的订单

-------
####添加模块
- 将下载的代码[order.py](https://wiki.mycapital.net/mycapital/upload/order.py)拷贝至策略代码中使用

-------
####示例代码
#####下载链接

```python
# encoding: utf-8

def on_init(context, config_type, config):
    context.order = Order(context, config)
    context.logger = Logger(context, config)
    context.position = config.contracts[0].today_pos['long_volume']
    context.order_sent_flag = False

    # order manager
    context.ordmgr = OrdMgr()


def on_book(context, quote_type, quote):
    if context.position > 0 and not context.order_sent_flag:
        _id = context.order.send_single_order(
            quote.symbol, quote.bp_array[0], 5, Direction.SELL, OpenClose.CLOSE
        )
        if _id > 0:  # SUCCESS
			context.ordmgr.send_order(
				_id, quote.symbol, quote.bp_array[0], 5, Direction.SELL, OpenClose.CLOSE
			)
			context.order_sent_flag = True
    elif 90000000 < quote.int_time < 90005000 and not context.order_sent_flag:
        _id = context.order.send_single_order(
            quote.symbol, quote.ap_array[0], 5, Direction.BUY, OpenClose.OPEN
        )
		if _id > 0:  # SUCCESS
			context.ordmgr.send_order(
				_id, quote.symbol, quote.ap_array[0], 5, Direction.BUY, OpenClose.OPEN
			)
			context.order_sent_flag = True
    else:
        pass


def on_response(context, response_type, response):
    context.ordmgr.on_response(response_type, response)
    # DEBUG INFO for order.py
    if context.ordmgr.active_orders:
        print('#' * 30, 'ACTIVE ORDERS', '#' * 30)
        for key,value in context.ordmgr.active_orders.items():
            print({key:value.__dict__})
    else:
        print('#' * 30, 'NO ACTIVE ORDER', '#' * 30)
```
