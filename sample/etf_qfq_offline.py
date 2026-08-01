#!/usr/bin/env python3
"""
离线批量下载 config_etf.yaml 中 ETF 的前复权日线数据。

日线数据从本地 tdxdir/vipdoc/{sh,sz}/lday/*.day 读取；XDXR 走
~/.mootdx2/xdxr/{symbol}.plk 24h 缓存（首次需联网）。每个 ETF 输出一个 CSV。

用法:
    # 从项目根目录跑, 日线走 tests/fixtures, 输出到 output/etf_qfq/
    python sample/etf_qfq_offline.py --tdxdir tests/fixtures

    # 限定前 10 个 ETF (调试用)
    python sample/etf_qfq_offline.py --tdxdir tests/fixtures --limit 10

    # 指定输出目录与配置文件
    python sample/etf_qfq_offline.py -c config_etf.yaml -d /path/to/tdx -o output/qfq
"""

import argparse
from pathlib import Path

import pandas as pd
import yaml

from mootdx2.reader import Reader
from mootdx2.tools.reversion import reversion


def load_etf_codes(config_path: str) -> list:
    """从 yaml 读取 ETF 代码列表"""
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return cfg['etf']


def fetch_qfq_offline(reader: Reader, symbol: str) -> pd.DataFrame:
    """离线获取单只 ETF 的前复权日线数据。

    Args:
        reader: 已构造的 Reader 实例
        symbol: ETF 代码

    Returns:
        前复权 OHLCV DataFrame, 索引为日期; 无数据时返回 None
    """
    raw = reader.daily(symbol=symbol, auto_download=True)
    if raw is None or raw.empty:
        return None

    xdxr = reader.xdxr(symbol=symbol)
    raw['code'] = symbol

    # reversion 会按 symbol 前缀自动分派: 15/16/50/51 走 etf_reversion (category==11),
    # 其余走 _reversion (category==1)
    qfq = reversion(symbol=symbol, stock_data=raw, xdxr=xdxr, type_='qfq')

    qfq.index = pd.to_datetime(qfq.index, utc=False)
    qfq = qfq.sort_index()

    # 统一 OHLCV 列
    if 'vol' in qfq.columns and 'volume' not in qfq.columns:
        qfq = qfq.rename(columns={'vol': 'volume'})

    cols = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in qfq.columns]
    return qfq[cols]


def main():
    parser = argparse.ArgumentParser(description='离线批量下载 ETF 前复权日线数据')
    parser.add_argument('-c', '--config', default='config_etf.yaml', help='ETF 代码 yaml 配置 (默认: config_etf.yaml)')
    parser.add_argument('-d', '--tdxdir', default=None, help='通达信数据目录, 默认按平台: Windows C:/new_tdx, macOS ~/new_tdx, Linux ~/.local/share/new_tdx')
    parser.add_argument('-o', '--output', default='output/etf_qfq', help='CSV 输出目录 (默认: output/etf_qfq)')
    parser.add_argument('-l', '--limit', type=int, default=None, help='只处理前 N 个 ETF (调试用)')
    args = parser.parse_args()

    codes = load_etf_codes(args.config)
    if args.limit:
        codes = codes[:args.limit]

    reader = Reader.factory(market='std', tdxdir=args.tdxdir)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    ok, fail, no_data = 0, 0, 0
    for i, code in enumerate(codes, 1):
        prefix = f'[{i}/{len(codes)}] {code}'
        try:
            df = fetch_qfq_offline(reader, code)
            if df is None or df.empty:
                print(f'{prefix} 无数据 (本地日线文件缺失或为空)')
                no_data += 1
                continue
            out_file = out_dir / f'{code}.csv'
            df.to_csv(out_file)
            print(f'{prefix} -> {out_file} ({len(df)} 条, {df.index[0].strftime("%Y-%m-%d")} ~ {df.index[-1].strftime("%Y-%m-%d")})')
            ok += 1
        except Exception as e:
            print(f'{prefix} 失败: {e}')
            fail += 1

    print(f'\n完成: 成功 {ok}, 无数据 {no_data}, 失败 {fail}, 共 {len(codes)} 个, 输出目录 {out_dir}')


if __name__ == '__main__':
    main()
