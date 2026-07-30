# coding:utf-8
"""
ETF 股息率数据获取示例

从 xdxr(除权除息) 数据中提取分红 (fenhong) 信息，并结合收盘价计算股息率。

股息率 = 年度分红总额 / 当前价格
"""

from datetime import datetime
import pandas as pd
from mootdx2.quotes import Quotes


def get_etf_dividend_yield(symbol, years=1):
    """
    获取 ETF 的股息率
    
    :param symbol: 股票代码 (如 '510050', '510300')
    :param years: 计算过去多少年的股息率，默认 1 年
    :return: DataFrame 包含分红信息和计算的股息率
    """
    
    # 创建 Quotes 客户端
    client = Quotes.factory(market='std', multithread=True, heartbeat=True)
    
    try:
        # 获取 xdxr(除权除息) 数据
        xdxr_data = client.xdxr(symbol=symbol)
        
        if xdxr_data is None or len(xdxr_data) == 0:
            print(f"No xdxr data found for {symbol}")
            return None
        
        # 获取最新收盘价
        latest_quotes = client.quotes(symbol=symbol)
        
        if latest_quotes is None or len(latest_quotes) == 0:
            print(f"No quotes data found for {symbol}")
            return None
        
        current_price = latest_quotes['price'].iloc[0]
        
        # 过滤分红记录 (category==1)
        dividend_records = xdxr_data[xdxr_data['category'] == 1].copy()

        if len(dividend_records) == 0:
            print(f"No dividend records found for {symbol}")
            return None

        # 创建日期列 - 使用字符串拼接方式避免 zip 迭代器问题
        date_strings = [f"{int(y)}-{int(m)}-{int(d)}" for y, m, d in
                        zip(dividend_records['year'].astype(int),
                            dividend_records['month'].astype(int),
                            dividend_records['day'].astype(int))]
        dividend_records['date'] = pd.to_datetime(date_strings, errors='coerce')

        # 按年份汇总分红
        dividend_records['year'] = dividend_records['date'].dt.year

        # 计算过去 N 年的总分红
        cutoff_date = datetime.now() - pd.Timedelta(days=years*365)
        recent_dividends = dividend_records[dividend_records['date'] >= cutoff_date]

        total_dividend = recent_dividends['fenhong'].sum()

        # 计算股息率
        dividend_yield = (total_dividend / current_price * 100) if current_price > 0 else 0

        # 构建结果
        result = pd.DataFrame({
            'symbol': [symbol],
            'current_price': [current_price],
            'total_dividend_1y': [total_dividend],
            'dividend_yield_1y_pct': [round(dividend_yield, 2)],
            'dividend_count_1y': [len(recent_dividends)]
        })

        print(f"\nETF: {symbol} ({dividend_records['name'].iloc[0] if 'name' in dividend_records.columns else ''})")
        print(f"当前价格：{current_price:.2f}")
        print(f"过去 {years}年分红总额：{total_dividend:.2f}")
        print(f"股息率：{dividend_yield:.2f}%")

        return result

    finally:
        client.close()


def get_detailed_dividend_history(symbol):
    """
    获取 ETF 的详细分红历史

    :param symbol: 股票代码
    :return: DataFrame 包含详细分红记录
    """

    client = Quotes.factory(market='std', multithread=True, heartbeat=True)

    try:
        xdxr_data = client.xdxr(symbol=symbol)

        if xdxr_data is None or len(xdxr_data) == 0:
            return None

        # 过滤分红记录 (category==1)
        dividend_records = xdxr_data[xdxr_data['category'] == 1].copy()

        if len(dividend_records) == 0:
            return None

        # 创建日期列并格式化 - 使用字符串拼接方式避免 zip 迭代器问题
        date_strings = [f"{int(y)}-{int(m)}-{int(d)}" for y, m, d in
                        zip(dividend_records['year'].astype(int),
                            dividend_records['month'].astype(int),
                            dividend_records['day'].astype(int))]
        dividend_records['date'] = pd.to_datetime(date_strings, errors='coerce')
        
        # 选择需要的列
        result = dividend_records[['date', 'fenhong']].copy()
        result.columns = ['分红日期', '每股分红 (元)']
        
        # 按日期降序排列
        result = result.sort_values('分红日期', ascending=False)
        
        print(f"\nETF {symbol} 分红历史:")
        print(result.to_string(index=False))
        
        return result
        
    finally:
        client.close()


if __name__ == '__main__':
    # 测试 ETF 股息率获取
    
    # 上证 50ETF
    print("=" * 60)
    print("示例 1: 获取上证 50ETF(510050) 的股息率")
    print("=" * 60)
    
    result1 = get_etf_dividend_yield('510050', years=1)
    
    print("\n" + "=" * 60)
    print("示例 2: 获取详细分红历史")
    print("=" * 60)
    
    get_detailed_dividend_history('510050')
    
    print("\n" + "=" * 60)
    print("示例 3: 获取沪深 300ETF(510300) 的股息率")
    print("=" * 60)
    
    result2 = get_etf_dividend_yield('510300', years=1)
    
    print("\n" + "=" * 60)
    print("说明:")
    print("=" * 60)
    print("""
    1. 股息率 = 年度分红总额 / 当前价格 × 100%
    
    2. 数据来源: 
       - xdxr(除权除息) 接口提供分红 (fenhong) 信息
       - quotes 接口提供当前价格
    
    3. 注意事项:
       - A 股 ETF 分红频率较低，通常每年 1-2 次
       - 股息率会随价格波动而变化
       - 历史分红不代表未来收益
    
    4. ETF 代码特征:
       - 上海证券交易所：51xxxx, 58xxxx
       - 深圳证券交易所：159xxx
    """)
