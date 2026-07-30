#!/usr/bin/env python3
"""
使用 mootdx2 获取前复权 K 线数据并绘制蜡烛图。

用法:
    python sample/candlestick_qfq.py 515880
    python sample/candlestick_qfq.py 515880 -n 120   # 绘制最近 120 根 K 线
    python sample/candlestick_qfq.py 600036 -n 90     # 也支持普通股票
"""

import sys

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from mootdx2.quotes import Quotes
from mootdx2.tools.reversion import reversion

# 设置中文字体，避免乱码
plt.rcParams['font.sans-serif'] = [
    'Arial Unicode MS',
    'Heiti SC',
    'PingFang SC',
    'SimHei',
    'WenQuanYi Micro Hei',
    'sans-serif',
]
plt.rcParams['axes.unicode_minus'] = False


def fetch_qfq_data(symbol: str, offset: int = 800) -> pd.DataFrame:
    """获取前复权 K 线数据。

    Args:
        symbol: 股票/ETF 代码，如 '515880'、'600036'
        offset: 获取的 K 线数量，默认 800 根

    Returns:
        前复权 OHLCV DataFrame，索引为日期
    """
    client = Quotes.factory(market='std', quiet=True)

    # 1. 获取不复权 K 线数据
    raw = client.bars(symbol=symbol, frequency=9, start=0, offset=offset)

    # 2. 获取除权除息 (XDXR) 数据
    xdxr_data = client.xdxr(symbol=symbol)

    # 3. reversion 要求 DataFrame 中有 'code' 列
    raw['code'] = symbol

    # 4. 前复权：type='01' 或 'qfq'
    qfq = reversion(symbol=symbol, stock_data=raw, xdxr=xdxr_data, type_='qfq')

    # 5. 构建日期索引，清理脏数据
    qfq.index = pd.to_datetime(qfq.index, utc=False)
    qfq = qfq.sort_index()

    # 只保留有有效 OHLCV 数据的行
    qfq = qfq.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    qfq = qfq[qfq['close'] > 0]  # 过滤 0 值（停牌等）

    # 选择需要的列
    if 'vol' in qfq.columns and 'volume' not in qfq.columns:
        cols = ['open', 'high', 'low', 'close', 'vol']
        result = qfq[cols].rename(columns={'vol': 'volume'})
    else:
        result = qfq[['open', 'high', 'low', 'close', 'volume']]

    return result


def plot_candlestick(df: pd.DataFrame, symbol: str, n_bars: int = 120):
    """绘制 K 线蜡烛图。

    Args:
        df: OHLCV DataFrame，索引为日期
        symbol: 股票代码
        n_bars: 绘制最近 N 根 K 线
    """
    data = df.tail(n_bars).copy()

    # 确保索引是 DatetimeIndex
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index, utc=False)

    title = f'{symbol} 前复权日K线图'

    mc = mpf.make_marketcolors(
        up='red',
        down='green',
        edge='inherit',
        wick='inherit',
        volume='inherit',
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='--',
        gridaxis='both',
        y_on_right=False,
    )

    mpf.plot(
        data,
        type='candle',
        style=style,
        title=title,
        ylabel='Price',
        ylabel_lower='Volume',
        volume=True,
        figsize=(16, 8),
        datetime_format='%m-%d',
        xrotation=30,
        tight_layout=True,
    )

    plt.show()


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else '515880'
    n_bars = 120

    # 解析 -n 参数
    args = sys.argv[1:]
    if '-n' in args:
        idx = args.index('-n')
        n_bars = int(args[idx + 1])
        # 当 -n 出现时，第一个参数仍然应是 stock code
        if not args[0].startswith('-'):
            symbol = args[0]
    elif len(sys.argv) > 2:
        n_bars = int(sys.argv[2])

    print(f'正在获取 {symbol} 的前复权 K 线数据...')
    df = fetch_qfq_data(symbol, offset=800)

    print(f'获取到 {len(df)} 条数据')
    print(f'日期范围: {df.index[0].strftime("%Y-%m-%d")} ~ {df.index[-1].strftime("%Y-%m-%d")}')
    print('\n最近 5 条数据:')
    print(df.tail())
    print(f'\n正在绘制最近 {n_bars} 根 K 线...')

    plot_candlestick(df, symbol, n_bars=n_bars)


if __name__ == '__main__':
    main()
