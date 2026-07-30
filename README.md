通达信数据读取接口
==================

运行环境
--------

-   操作系统: Windows / MacOS / Linux 都可以运行.
-   Python: 3.8 以及以上版本.

安装方法
--------

> 新手建议使用 `pip install -U 'mootdx2[all]'` 安装

### PIP 安装方法
```shell
pip install mootdx2
```

### 升级安装

```shell
pip install -U mootdx2
```

### 开发环境安装

推荐使用 `uv` 进行开发环境管理：

```shell
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆代码
git clone https://github.com/mootdx/mootdx.git
cd mootdx

# 同步依赖
uv sync

# 运行测试
uv run pytest
```

使用说明
--------

> 以下只列举一些例子, 详细说明请查看在线文档: <https://www.mootdx.com>

通达信离线数据读取

```python
from mootdx2.reader import Reader

# market 参数 std 为标准市场(就是股票), ext 为扩展市场(期货，黄金等)
# tdxdir 是通达信的数据目录, 根据自己的情况修改

reader = Reader.factory(market='std', tdxdir='C:/new_tdx')

# 读取日线数据
reader.daily(symbol='600036')

# 读取分钟数据
reader.minute(symbol='600036')

# 读取时间线数据
reader.fzline(symbol='600036')
```

通达信线上行情读取

```python
from mootdx2.quotes import Quotes

# 标准市场
client = Quotes.factory(market='std', multithread=True, heartbeat=True)

# k 线数据
client.bars(symbol='600036', frequency=9, offset=10)

# 指数
client.index(symbol='000001', frequency=9)

# 分钟
client.minute(symbol='000001')
```

通达信财务数据读取

```python
from mootdx2.affair import Affair

# 远程文件列表
files = Affair.files()

# 下载单个
Affair.fetch(downdir='tmp', filename='gpcw19960630.zip')

# 下载全部
Affair.parse(downdir='tmp')
```
--------

M1 mac 系统PyMiniRacer不能使用，访问:
<https://github.com/sqreen/PyMiniRacer/issues/143>

