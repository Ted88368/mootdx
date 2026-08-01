import logging

import pandas as pd

from mootdx2.utils.factor import fq_factor

logger = logging.getLogger(__name__)


def factor_reversion(symbol: str, method: str = 'qfq', raw: pd.DataFrame = None) -> pd.DataFrame:
    factor = fq_factor(symbol, method)

    if not factor.empty:
        factor = factor.sort_index(ascending=True)
        raw = raw.sort_index(ascending=True)

        data = pd.concat([raw, factor.loc[raw.index[0]: raw.index[-1], ['factor']]], axis=1)
        data.factor = data.factor.bfill(axis=0) if method == 'qfq' else data.factor.ffill(axis=0)
        data.factor = data.factor.fillna(1.0, axis=0)
        data.factor = data.factor.astype(float)

        for col in ['open', 'high', 'low', 'close', ]:
            data[col] = data[col] * data['factor']

        return data

    return raw


def _reversion(bfq_data, xdxr_data, type_):
    if len(bfq_data) <= 0:
        return bfq_data

    if len(xdxr_data) <= 0:
        return bfq_data

    """使用数据库数据进行复权"""
    info = xdxr_data.query('category==1')
    bfq_data = bfq_data.assign(if_trade=1)

    if len(info) > 0:
        # 有除权数据
        data = pd.concat([bfq_data, info.loc[bfq_data.index[0]: bfq_data.index[-1], ['category']]], axis=1)
        data['if_trade'] = data['if_trade'].fillna(value=0)

        data = data.ffill()
        data = pd.concat(
            [data, info.loc[bfq_data.index[0]: bfq_data.index[-1], ['fenhong', 'peigu', 'peigujia', 'songzhuangu']]],
            axis=1)
    else:
        data = pd.concat([bfq_data, info.loc[:, ['category', 'fenhong', 'peigu', 'peigujia', 'songzhuangu']]], axis=1)

    # 数据补全
    data = data.fillna(0)

    # 计算前日收盘
    data['preclose'] = (data['close'].shift(1) * 10 - data['fenhong'] + data['peigu'] * data['peigujia']) / (
        10 + data['peigu'] + data['songzhuangu'])

    # 前复权
    if type_.lower() in ['01', 'qfq']:
        data['adj'] = (data['preclose'].shift(-1) / data['close']).fillna(1)[::-1].cumprod()
        # ohlc 数据进行复权计算
        for col in ['open', 'high', 'low', 'close', 'preclose']:
            data[col] = data[col] * data['adj']

    # 后复权
    if type_.lower() in ['02', 'hfq']:
        data['adj'] = (data['preclose'].shift(-1) / data['close']).fillna(1).cumprod()
        for col in ['open', 'high', 'low', 'close', 'preclose']:
            data[col] = data[col] / data['adj']

    # data["volume"] = data.get("volume", data.get("vol"))
    data['volume'] = data['volume'] / data['adj']
    # data['volume'] = data['volume'] / data['adj'] if 'volume' in data.columns else data['vol'] / data['adj']

    try:
        # 大该是涨跌幅
        data['high_limit'] = data['high_limit'] * data['adj']
        data['low_limit'] = data['low_limit'] * data['adj']
    except:
        pass

    data = data.query('if_trade==1 and open != 0')
    data = data.drop(['fenhong', 'peigu', 'peigujia', 'songzhuangu', 'if_trade', 'category'], axis=1, errors='ignore')

    return data


def etf_reversion(data, xdxr, adjust='01'):
    if len(data) <= 0:
        return data

    if len(xdxr) <= 0:
        return data

    xdxr = xdxr.query('category==11')

    if len(xdxr) <= 0:
        return data

    # Build date column from available date-related fields
    if 'year' in data.columns and 'month' in data.columns and 'day' in data.columns:
        data['date'] = pd.to_datetime(data[['year', 'month', 'day']], utc=False)
    elif 'datetime' in data.columns:
        data['date'] = pd.to_datetime(data['datetime'], utc=False)
    elif isinstance(data.index, pd.DatetimeIndex):
        data['date'] = data.index
    else:
        data['date'] = pd.to_datetime(data.index, utc=False)

    data = data.set_index(['date'])
    data = pd.concat([data, xdxr.loc[data.index[0]: data.index[-1], ['suogu', 'category']]], axis=1)

    if adjust.lower() in ['01', 'qfq']:
        # 获取 suogu 事件日期的原始值（仅在除权日有非空值）
        suogu_raw = data['suogu'].dropna().sort_index()

        if len(suogu_raw) > 0:
            # 从后往前累积乘积：前复权 = 历史价格除以累积因子
            cum_suogu = suogu_raw[::-1].cumprod()[::-1]

            # 将累积因子赋值回原始数据的事件日期
            data['suogu'] = pd.Series(index=data.index, dtype=float)
            data.loc[cum_suogu.index, 'suogu'] = cum_suogu.values

            # 向后填充（前复权：向前传播累积因子）
            data['suogu'] = data['suogu'].bfill()
            data['suogu'] = data['suogu'].fillna(1)

            # 前移一天：除权日当天价格已是除权后的，不参与调整
            data['suogu'] = data['suogu'].shift(-1)
            data['suogu'] = data['suogu'].fillna(1)

            for col in ['open', 'high', 'low', 'close']:
                data[col] = data[col] / data['suogu']

    if adjust.lower() in ['02', 'hfq']:
        # 获取 suogu 事件日期的原始值（仅在除权日有非空值）
        suogu_raw = data['suogu'].dropna().sort_index()

        if len(suogu_raw) > 0:
            # 从前往后累积乘积：后复权 = 未来价格乘以累积因子
            cum_suogu = suogu_raw.cumprod()

            # 将累积因子赋值回原始数据的事件日期
            data['suogu'] = pd.Series(index=data.index, dtype=float)
            data.loc[cum_suogu.index, 'suogu'] = cum_suogu.values

            # 向前填充（后复权：向后传播累积因子）
            data['suogu'] = data['suogu'].ffill()
            data['suogu'] = data['suogu'].fillna(1)

            for col in ['open', 'high', 'low', 'close']:
                data[col] = data[col] * data['suogu']

    data = data.drop(['suogu', 'category'], axis=1, errors='ignore')
    # Restore index: prefer 'datetime' column if it exists, otherwise keep 'date' index
    if 'datetime' in data.columns:
        data = data.set_index(['datetime'])
    else:
        data.index.name = 'datetime'

    return data


def reversion(symbol, stock_data, xdxr, type_='01'):
    def _fetch_xdxr(collections=None) -> pd.DataFrame:
        """获取股票除权信息数据"""
        columns = [
            'category',
            'category_meaning',
            'date',
            'fenhong',
            'fenshu',
            'liquidity_after',
            'liquidity_before',
            'name',
            'peigu',
            'peigujia',
            'shares_after',
            'shares_before',
            'songzhuangu',
            'suogu',
            'xingquanjia',
        ]

        try:
            data = collections

            if data is None:
                return pd.DataFrame(data=[], columns=columns)

            if len(data) <= 0:
                return data

            if 'date' not in data.columns:
                data['date'] = pd.to_datetime(data[['year', 'month', 'day']], utc=False)
                data = data.set_index(['date'])

            # data = data.drop(['year', 'month', 'day', ], axis=1)
            # data = pd.DataFrame([item for item in collections.find({"code": symbol})]).drop(["_id"], axis=1)
            # data = collections
            # data["date"] = pd.to_datetime(data["date"], utc=False)
            # data["date"] = pd.to_datetime(xdxr[["year", "month", "day"]], utc=False)
            # return data.set_index(["date", "code"], drop=False)
            return data
        except Exception as ex:
            logger.error(ex)
            return pd.DataFrame(data=[], columns=columns)

    # '股票 日线/分钟线 动态复权接口'
    # if isinstance(stock_data.index, pd.MultiIndex):
    #     symbol = stock_data.index.remove_unused_levels().levels[1][0]
    # else:
    #     symbol = stock_data["code"][0]
    # symbol = ''
    # symbol = (
    #     stock_data.index.remove_unused_levels().levels[1][0]
    #     if isinstance(stock_data.index, pd.MultiIndex)
    #     else stock_data["code"][0]
    # )

    xdxr = _fetch_xdxr(xdxr)
    if len(xdxr) <= 0:
        return stock_data

    # 基金类代码 (15/16/50/51 前缀: ETF/LOF/封基) 走 etf_reversion (category==11)，
    # 跳过 _reversion 的二次处理，避免对已复权数据再复权
    if symbol[:2] in ['15', '16', '50', '51']:
        try:
            return etf_reversion(data=stock_data, xdxr=xdxr, adjust=type_)
        except Exception as ex:
            logger.warning(f'ETF reversion failed for %s, falling back to Sina factor: %s', symbol, ex)
    else:
        try:
            return _reversion(bfq_data=stock_data, xdxr_data=xdxr, type_=type_)
        except Exception as ex:
            logger.warning(f'XDXR reversion failed for %s, falling back to Sina factor: %s', symbol, ex)

    # Fallback: Sina finance precomputed factor
    try:
        return factor_reversion(symbol=symbol, raw=stock_data, method=type_)
    except Exception as ex2:
        logger.error(f'Sina factor reversion also failed for %s: %s', symbol, ex2)
        return stock_data


# 算法一样
def baoli_qfq(df, xdxr):
    peigu = xdxr['peigu']  # 配股
    fenhong = xdxr['fenhong']  # 分红
    peigujia = xdxr['peigujia']  # 配股价
    songzhuangu = xdxr['songzhuangu']  # 送转股

    for i in range(0, len(xdxr)):
        fh = fenhong[i]
        pg = peigu[i]
        pgj = peigujia[i]
        szg = songzhuangu[i]
        date = xdxr.index[i]

        df.loc[df.index < date, 'close'] = (df['close'][df.index < date] * 10 - fh + pg * pgj) / (10 + pg + szg)
        df.loc[df.index < date, 'open'] = (df['open'][df.index < date] * 10 - fh + pg * pgj) / (10 + pg + szg)
        df.loc[df.index < date, 'high'] = (df['high'][df.index < date] * 10 - fh + pg * pgj) / (10 + pg + szg)
        df.loc[df.index < date, 'low'] = (df['low'][df.index < date] * 10 - fh + pg * pgj) / (10 + pg + szg)

    return df
