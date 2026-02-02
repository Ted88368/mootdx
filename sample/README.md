# Sample 示例目录

本目录包含 mootdx 库的各种使用示例，帮助用户快速了解如何使用不同的功能模块。

## 数据下载示例

### 行情数据下载

- **`basic_quotes.py`** - A股行情数据下载示例
  - 使用标准市场客户端下载A股K线数据
  - 支持前复权 (qfq)、后复权 (hfq) 等复权方式
  - 示例：下载浦发银行 (600036) 的K线数据

- **`hk_quotes.py`** - 港股行情数据下载示例
  - 使用扩展市场客户端下载港股数据
  - 支持香港主板 (market=47) 和创业板 (market=48)
  - 示例：下载腾讯控股 (00700) 的日K线数据

### 财务数据下载

- **`basic_affairs.py`** - 获取财务数据文件列表
  - 使用 `Affair.files()` 查看可用的财务数据文件
  - 显示文件名、大小和哈希值

- **`parse_affairs_all.py`** - 批量下载和解析财务数据
  - 使用 `Affair.fetch()` 下载全部财务数据到 tmp 目录
  - 自动解析 zip 文件并导出为 CSV 格式
  - 合并所有数据到 all.csv

## 数据处理示例

### 数据读取

- **`basic_reader.py`** - 本地数据读取示例
  - 演示如何读取已下载的本地数据文件
  - 使用 Reader 类进行数据访问

### 复权计算

- **`basic_adjust.py`** - 基础复权计算示例
  - 演示如何对股票数据进行复权处理
  - 支持前复权和后复权计算

- **`fuquan.py`** - 复权功能详细示例
  - 更详细的复权计算演示
  - 包含多种复权场景

- **`fq.py`** - 复权算法实现
  - 复权相关的核心算法和工具函数

## 工具和辅助示例

- **`verify_server.py`** - 服务器验证
  - 验证数据服务器的连接状态
  - 检查服务器可用性

- **`list_ext_markets.py`** - 列出扩展市场
  - 查看所有可用的扩展市场列表
  - 包括港股、美股等市场信息

- **`lru_cache.py`** - 缓存使用示例
  - 演示如何使用 LRU 缓存优化数据访问性能

## 快速开始

### 下载A股数据

```python
from mootdx.quotes import Quotes

client = Quotes.factory(market="std", quiet=True)

# 获取K线数据 (不复权)
df = client.bars(symbol='600036', frequency=9, start=0, offset=100)
print(df.head())

# 如果需要复权数据
from mootdx.tools.reversion import reversion
xdxr_data = client.xdxr(symbol='600036')
df['code'] = '600036'
qfq_df = reversion(df, xdxr_data, '01')  # '01' 表示前复权, '02' 表示后复权
print(qfq_df.head())
```

### 下载港股数据

```python
from mootdx.quotes import Quotes

client = Quotes.factory(market='ext')
bars = client.bars(frequency=9, market=47, symbol='00700', start=0, offset=100)
print(bars)
```

### 下载财务数据

```python
from mootdx.affair import Affair

# 下载所有财务数据
Affair.fetch(downdir="tmp")

# 解析指定文件
data = Affair.parse(downdir="tmp", filename="gpcw19960630.zip")
```

## 注意事项

1. 运行示例前请确保已正确安装 mootdx 库
2. 某些示例需要网络连接才能下载数据
3. 下载的数据文件会保存在指定的目录中（如 tmp 目录）
4. 建议先运行 `verify_server.py` 确认服务器连接正常

## 相关文档

- [主项目 README](../README.md)
- [API 文档](https://mootdx.readthedocs.io/)
