#!/usr/bin/env python3
"""
使用 mootdx2 获取前复权 K 线数据并绘制蜡烛图。

用法:
    uv run  sample/candlestick_qfq.py 515880
    python sample/candlestick_qfq.py 515880 -n 120   # 绘制最近 120 根 K 线
    python sample/candlestick_qfq.py 600036 -n 90     # 也支持普通股票

离线模式 (从本地通达信数据目录读取，需先有 ~/.mootdx2/xdxr/{symbol}.plk 缓存或首次联网拉取):
    python sample/candlestick_qfq.py 515880 --offline --tdxdir /path/to/tdx
    python sample/candlestick_qfq.py 600036 --offline --tdxdir tests/fixtures
"""

import argparse

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from mootdx2.quotes import Quotes
from mootdx2.reader import Reader
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


def fetch_qfq_online(symbol: str, offset: int = 800) -> pd.DataFrame:
    """在线获取前复权 K 线数据。

    Args:
        symbol: 股票/ETF 代码，如 '515880'、'600036'
        offset: 获取的 K 线数量，默认 800 根

    Returns:
        前复权 OHLCV DataFrame，索引为日期
    """
    client = Quotes.factory(market='std', quiet=True)
    raw = client.bars(symbol=symbol, frequency=9, start=0, offset=offset)
    xdxr_data = client.xdxr(symbol=symbol)
    return _reversion_and_normalize(symbol, raw, xdxr_data)


def fetch_qfq_offline(symbol: str, tdxdir: str) -> pd.DataFrame:
    """离线获取前复权 K 线数据（从本地通达信数据目录读取）。

    XDXR 数据走 ``~/.mootdx2/xdxr/{symbol}.plk`` 24h 缓存：命中即纯离线读取，
    未命中则联网拉取并写回缓存。日线数据从 ``tdxdir/vipdoc/{sh,sz}/lday/*.day``
    读取。

    Args:
        symbol: 股票/ETF 代码，如 '600036'
        tdxdir: 通达信安装目录

    Returns:
        前复权 OHLCV DataFrame，索引为日期
    """
    reader = Reader.factory(market='std', tdxdir=tdxdir)
    raw = reader.daily(symbol=symbol)
    if raw is None or raw.empty:
        raise FileNotFoundError(f'在 {reader.tdxdir} 下未找到 {symbol} 的本地日线数据，请确认通达信目录与代码')
    xdxr_data = reader.xdxr(symbol=symbol)
    return _reversion_and_normalize(symbol, raw, xdxr_data)


def _reversion_and_normalize(symbol: str, raw: pd.DataFrame, xdxr_data: pd.DataFrame) -> pd.DataFrame:
    """对不复权 OHLCV 数据应用前复权并清理。

    Args:
        symbol: 股票/ETF 代码
        raw: 不复权 OHLCV DataFrame（在线 bars 或离线 daily 返回）
        xdxr_data: 除权除息 DataFrame（在线 xdxr 或离线缓存返回）

    Returns:
        前复权 OHLCV DataFrame，索引为日期
    """
    # reversion 要求 DataFrame 中有 'code' 列
    raw['code'] = symbol

    # 前复权：type='01' 或 'qfq'
    qfq = reversion(symbol=symbol, stock_data=raw, xdxr=xdxr_data, type_='qfq')

    # 构建日期索引，清理脏数据
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

    # 确保数值列为 float 类型
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce')

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
    parser = argparse.ArgumentParser(description='使用 mootdx2 获取前复权 K 线数据并绘制蜡烛图')
    parser.add_argument('symbol', nargs='?', default='515880', help='股票/ETF 代码 (默认: 515880)')
    parser.add_argument('-n', '--n-bars', type=int, default=120, help='绘制最近 N 根 K 线 (默认: 120)')
    parser.add_argument('--offline', action='store_true', help='使用本地通达信数据 (未指定 --tdxdir 时按平台默认)')
    parser.add_argument('--tdxdir', default=None, help='通达信安装目录, 默认按平台: Windows C:/new_tdx, macOS ~/new_tdx, Linux ~/.local/share/new_tdx')
    args = parser.parse_args()

    symbol = args.symbol
    n_bars = args.n_bars

    if args.offline:
        tdxdir_desc = args.tdxdir if args.tdxdir else '(平台默认)'
        print(f'正在从本地通达信目录 {tdxdir_desc} 读取 {symbol} 的前复权 K 线数据...')
        df = fetch_qfq_offline(symbol, tdxdir=args.tdxdir)
    else:
        print(f'正在在线获取 {symbol} 的前复权 K 线数据...')
        df = fetch_qfq_online(symbol, offset=800)

    print(f'获取到 {len(df)} 条数据')
    print(f'日期范围: {df.index[0].strftime("%Y-%m-%d")} ~ {df.index[-1].strftime("%Y-%m-%d")}')
    print('\n最近 5 条数据:')
    print(df.tail())
    print(f'\n正在绘制最近 {n_bars} 根 K 线...')

    plot_candlestick(df, symbol, n_bars=n_bars)


if __name__ == '__main__':
    main()
