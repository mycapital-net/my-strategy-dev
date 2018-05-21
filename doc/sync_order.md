因实盘策略交易过程中可能出现因前面的订单未撤导致后面追单的订单因资金不足被风控拦截的问题，现提供一个同步发单的模块，建议实盘采用此种方式。

模块具体描述如下：
- 提供基本的订单管理以及封装好的同步下单撤单模块。
- 若某合约有正在被撤的订单，调用下单接口会将订单缓存起来，待到下一个撤单成功的回报回来发出订单。
- 需要策略中主动调用的有:
	- `SyncOrder.__init__` 初始化函数
	- `SyncOrder.on_response`更新回报
	- `SyncOrder.send_single_order` 替换原始API中的`Order.send_single_order`下单
	- `SyncOrder.cancel_single_order` 替换原始的`Order.cancel_single_order`撤单
	- `SyncOrder.clear_delayed_orders` 清空缓存订单

####发单逻辑
----
- 若策略正在撤单且没有收到撤单回报，此时调用发单函数会将订单缓存在`SyncOrder._delayed_orders`中。
- 当收到撤单回报后，自动将缓存的订单发出。
- 如果发单过程希望清空缓存的订单，可以通过调用`SyncOrder.clear_delayed_orders`方法实现。

####添加模块
----
- 下载源码并拷贝至策略所在目录
- 通过`from sync_order import SyncOrder`添加模块
- [下载链接](https://wiki.mycapital.net/mycapital/upload/sync_order.py)

####示例代码
```python
from sync_order import SyncOrder
from my.sdp.api import Direction, OpenClose

def on_init(context, config_type, config):
	# *********初始化**********
	context.order = SyncOrder(context, config)
	......

def on_book(context, quote_type, quote):
	......
	# 同步发单, 如果撤单回报未返回，存储订单并推迟到撤单成功后发出。
	context.order.send_single_order(
		quote.symbol, quote.bp_array[0], 1, Direction.SELL, OpenClose.OPEN
	)
	# 撤单, 记录撤单状态
	context.order.cancel_single_order(1)
	# 获取挂单信息、因撤单回报延迟的订单信息
	print(context.order.active_orders)
	print(context.order.delayed_orders)
	# 提供封装的日志函数，通过SyncOrder.debug来控制打印开关
	context.order.info("DEBUG INFO: ")
	# 主动取消所有存储未发出的订单
	context.order.clear_delayed_orders()


def on_response()
	# *********更新回报状态**********
	context.order.on_response(response_type, response)
	......
```