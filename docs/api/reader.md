## 离线数据接口

通过下面的接口，我们可以解析日K线文件，该文件可以通过读取软件本地目录导出的数据获取，也可以从官网上下载， 如果您安装了终端，可以在安装目录下找到 `vipdoc` 子目录。

比如我的客户端安装在 `c:\new_tdx` 下，

即

- `C:/new_tdx/vipdoc/sz/lday/` 下是深圳的日k线数据
- `C:/new_tdx/vipdoc/sh/lday/` 下是上海的日k线数据

该目录下每个股票为一个文件，如 `sz000001.day` 为深圳的日k行情，

### 离线模式 vs 在线模式

mootdx2 提供两条数据通路，返回 schema 一致，可按场景选用：

| | 在线模式 (`Quotes`) | 离线模式 (`Reader`) |
|---|---|---|
| **日线数据** | `Quotes.bars()` 走 TDX 行情服务器 (7709 端口) 拉取 | `Reader.daily()` 读本地 `tdxdir/vipdoc/{sh,sz}/lday/*.day` 文件 |
| **XDXR 数据** | `Quotes.xdxr()` 走 TDX 服务器拉取 | `Reader.xdxr()` 读 `~/.mootdx2/xdxr/{symbol}.plk` 24h 缓存，未命中则联网拉取并写回 |
| **网络依赖** | 每次都要联网 | 日线纯本地；XDXR 首次/过期需联网一次 |
| **数据时效** | 最新（实时/最新收盘） | 取决于本地通达信客户端上次下载到什么时候 |
| **条数控制** | `offset` 服务器端分页 | 读整个 `.day` 文件，调用方自行截取 |
| **前置条件** | 能连上 TDX 服务器 | 本地有通达信数据目录（`tdxdir` 或平台默认） |

> **离线模式的 XDXR 不是纯离线**：本地 `gbbq` 文件加密无法解析，`Reader.xdxr()` 复用在线 `get_xdxr()` 的 24h pickle 缓存。要完全断网运行，需之前在同一台机器上跑过一次（或手动放过 `.plk` 缓存）。

```python
# 在线模式
from mootdx2.quotes import Quotes
client = Quotes.factory(market='std', quiet=True)
raw = client.bars(symbol='600036', frequency=9, start=0, offset=800)
xdxr = client.xdxr(symbol='600036')

# 离线模式
from mootdx2.reader import Reader
reader = Reader.factory(market='std', tdxdir='C:/new_tdx')  # tdxdir 可省略, 走平台默认
raw = reader.daily(symbol='600036')
xdxr = reader.xdxr(symbol='600036')
```

两条路后面都可走 `reversion(symbol, stock_data=raw, xdxr=xdxr, type_='qfq')` 做前复权，输出一致。

### 01. 读取行情接口

```python
from mootdx2.reader import Reader

# tdxdir 默认按平台: Windows C:/new_tdx, macOS ~/new_tdx, Linux ~/.local/share/new_tdx
reader = Reader.factory(market='std', tdxdir='C:/new_tdx')

# 读取日线数据
reader.daily(symbol='600036')

# 读取1分钟数据
reader.minute(symbol='600036')

# 读取5分钟数据
reader.fzline(symbol='600036')

# 读取除权除息 (XDXR) 数据
reader.xdxr(symbol='600036')
```

#### reader.xdxr(symbol)

读取除权除息（XDXR）信息，返回 schema 与在线接口 `Quotes.xdxr()` 一致，可直接喂给 `reversion()` 做前复权/后复权。

本地 `gbbq` 文件为加密格式（密钥硬编码在 `tdxw.exe` 内，无法直接解析），因此 `reader.xdxr()` 复用 `~/.mootdx2/xdxr/{symbol}.plk` 的 24h pickle 缓存：

- **缓存命中**（24h 内跑过）：纯离线，零网络
- **缓存未命中/过期**：联网拉取一次并写回缓存

返回 DataFrame 列含 `year/month/day/category/name/fenhong/peigujia/songzhuangu/peigu/suogu/.../code`，索引为 `date` (DatetimeIndex)。

配合 `daily()` + `reversion()` 画前复权 K 线：

```python
from mootdx2.reader import Reader
from mootdx2.tools.reversion import reversion

reader = Reader.factory(market='std', tdxdir='C:/new_tdx')
raw = reader.daily(symbol='600036')
xdxr = reader.xdxr(symbol='600036')
raw['code'] = '600036'
qfq = reversion(symbol='600036', stock_data=raw, xdxr=xdxr, type_='qfq')
```

> 也可以直接 `reader.daily(symbol='600036', adjust='qfq')`，内部自动走 `to_data` → `to_adjust` → `reversion` → `get_xdxr`（同样走 24h 缓存）。

## 02. 读取扩展行情

> 读取扩展行情的日线（如期货，期权，现货等）

```python

from mootdx2.reader import Reader

reader = Reader.factory(market='ext', tdxdir='c:/new_tdx')
reader.daily(symbol='29#A1801')
```

## 03. 历史分钟数据

> 读取分钟K线（目前支持1，5分钟k线）

分钟线有两种格式，第一种是`.1` `.5` 为后缀的, 还有一种为 `.lc1` `.lc5` 后缀的. 不过不用考虑，接口会自动判断

```python
from mootdx2.reader import Reader

reader = Reader.factory(market='std', tdxdir='c:/new_tdx')
reader.minute(symbol='000001', suffix='1')  # suffix = 1 一分钟，5 五分钟
```

扩展数据接口读取方式

```python
from mootdx2.reader import Reader

reader = Reader.factory(market='ext', tdxdir='c:/new_tdx')
reader.minute(symbol='000001', suffix='1')  # suffix = 1 一分钟，5 五分钟
```

## 04. 读取板块信息

文件位置参考： [http://blog.sina.com.cn/s/blog_623d2d280102vt8y.html](http://blog.sina.com.cn/s/blog_623d2d280102vt8y.html)

样例代码：

```python
from mootdx2.reader import Reader

reader = Reader.factory(market='std', tdxdir='c:/new_tdx')
reader.block(symbol='block_zs', group=False)
```

```python
# 分组格式
from mootdx2.reader import Reader
reader = Reader.factory(market='std', tdxdir='c:/new_tdx')

reader.block(symbol='block_zs', group=True)
```

## 05. 自定义板块数据

> 读取自定义板块信息文件夹

```python
import mootdx2.block
from mootdx2.reader import Reader

reader = Reader.factory(market='std', tdxdir='C:/new_tdx')

# 默认扁平格式
reader.block_new()

# 分组格式
reader.block_new(group=True)
```

写入新板块

```python
# 写入新板块
import mootdx2.block
from mootdx2.reader import Reader

reader = Reader.factory(market='std', tdxdir='C:/new_tdx')
reader.block_new(name='最优盈利板块', symbol=['600001', '600002', '600003', '600004', ])
```
