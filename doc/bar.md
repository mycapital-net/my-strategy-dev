部分策略需要基于一段时间的bar行情实现逻辑，平台除直接提供bar行情数据外，同时提供一个简单模块用于从tick数据构造bar数据。由 BarGenerator 类实现。
- tick构造bar功能
    - 初始化时创建一个 `BarGenerator` 的实例，并传入bar的时间间隔(分钟)
    - 在每笔tick行情到来时调用`process_bar_data()`接口更新新的bar数据并传入`on_book`的函数对象
    - 当行情时间达到bar的时间间隔，BarGenerator将主动回调策略传入的`on_book`函数, 行情类型为3。


-------
####添加模块
- 将下载的代码[bar.py](https://wiki.mycapital.net/mycapital/upload/bar.py)拷贝至策略代码中使用


-------

####示例代码

```python
# encoding: utf-8

def on_init(context, config_type, config):
    # bar generator, interval is 1min
    context.bar_generator = BarGenerator(1)


def on_book(context, quote_type, quote):
    context.bar_generator.process_bar_data(context, quote_type, quote, on_book)

    # DEBUG INFO for BAR
    if quote_type==3:
        print (quote.__dict__)
```
