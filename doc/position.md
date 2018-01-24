此模块提供基本的仓位管理和盘中Pnl计算功能，由 PosMgrBase 类实现。
- 仓位管理功能
    - 初始化时创建一个 `PosMgrBase` 的实例
    - 策略初始化时需要调用`init_position()`接口根据传入的config更新合约的初始仓位
    - 收到回报时需要调用`update_position()`接口根据回报更新实时仓位
- pnl功能
    - 收到行情时需要调用`update_last_px()`接口更新合约的最新价
    - 根据仓位中的 多开、多平、空开、空平 量价与合约最新价计算平仓与持仓盈亏
---------
####查询接口
- 仓位

|	函数名	|	描述	|	参数	|	返回	|
|	:------------	|	:------------	|	:------------	|	:------------		|
|get_long_position|获取目前的多仓仓位|str：symbol 合约名|int：返回多仓仓位|
|get_short_position|获取目前的空仓仓位|str：symbol 合约名|int：返回空仓仓位|
|get_net_position|获取目前的净仓位|str：symbol 合约名|int：返回净仓位|
|get_yes_position|获取昨仓仓位|str：symbol 合约名|dict：昨仓仓位 ```{"long": {"pos", "notional"},"short": {"pos", "notional"}}```|
|get_avg_position_price|获取目前的持仓平均价|str：symbol 合约名, int：direction 方向|float：返回价格|
|get_sell_open_avg_px|获取目前的空开平均价|str：symbol 合约名|float：返回价格|
|get_buy_open_avg_px|获取目前的多开平均价|str：symbol 合约名|float：返回价格|

- PnL

|	函数名	|	描述	|	参数	|	返回	|
|	:------------	|	:------------	|	:------------	|	:------------		|
|get_realized_pnl|获取合约当前的平仓盈亏|str：symbol 合约名|float：返回盈亏(点数)|
|get_unrealized_pnl|获取合约当前的持仓盈亏|str：symbol 合约名|float：返回盈亏(点数)|
|get_contract_pnl_cash|获取合约当前的总盈亏|str：symbol 合约名|float：返回盈亏|
|get_strategy_pnl_cash|获取策略当前的总盈亏|None|float：返回盈亏|
注： 点数 * contract.multiple = 现金金额

-------
####添加模块
- 将下载的代码[position.py](https://wiki.mycapital.net/mycapital/upload/position.py)拷贝至策略代码中使用

-------
####示例代码

```python
# encoding: utf-8

def on_init(context, config_type, config):
    context.order = Order(context, config)
    context.logger = Logger(context, config)
    context.position = config.contracts[0].today_pos['long_volume']
    context.order_sent_flag = False

    # position manager
    context.posmgr = PosMgrBase()
    context.posmgr.init_position(config_type, config)


def on_book(context, quote_type, quote):
    context.posmgr.update_last_px(quote_type, quote)

    if context.position > 0 and not context.order_sent_flag:
        _id = context.order.send_single_order(
            quote.symbol, quote.bp_array[0], 5, Direction.SELL, OpenClose.CLOSE
        )
        context.order_sent_flag = True
    elif 90000000 < quote.int_time < 90005000 and not context.order_sent_flag:
        _id = context.order.send_single_order(
            quote.symbol, quote.ap_array[0], 5, Direction.BUY, OpenClose.OPEN
            )
        context.order_sent_flag = True
    else:
        pass


def on_response(context, response_type, response):
    context.posmgr.update_position(response_type, response)

    # DEBUG INFO for position.py
    print (
        "long_position: " , context.posmgr.get_long_position(response.symbol), "\n"
        "short_position: " , context.posmgr.get_short_position(response.symbol), "\n"
        "net_position: " , context.posmgr.get_net_position(response.symbol), "\n"
        "yes_position: " , context.posmgr.get_yes_position(response.symbol), "\n"
        "avg_position_price_buy: " , context.posmgr.get_avg_position_price(response.symbol, Direction.BUY), "\n"
        "avg_position_price_sell: " , context.posmgr.get_avg_position_price(response.symbol, Direction.SELL), "\n"
        "sell_open_avg_px: " , context.posmgr.get_sell_open_avg_px(response.symbol), "\n"
        "buy_open_avg_px: " , context.posmgr.get_buy_open_avg_px(response.symbol), "\n"
        "pnl: " , context.posmgr.get_strategy_pnl_cash(), "\n"
    )
```
