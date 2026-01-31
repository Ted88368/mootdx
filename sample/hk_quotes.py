from mootdx.quotes import Quotes

# 扩展市场客户端 - 包括港股
client = Quotes.factory(market='ext')

# 获取市场列表
markets = client.markets()
print("可用市场:")
print(markets)

# 港股市场 ID 通常是 47 或 48
# 47 - 香港主板 (HK)
# 48 - 香港创业板 (KG)

# 查询港股行情示例 (腾讯控股: 00700)
if __name__ == '__main__':
    # 获取港股五档行情
    # market=47 表示香港主板
    # quote = client.quote(market=47, symbol='00700')
    # print("\n腾讯控股(00700)五档行情:")
    # print(quote)
    
    # # 获取港股分时行情
    # minute = client.minute(market=47, symbol='00700')
    # print("\n腾讯控股(00700)分时行情:")
    # print(minute)
    
    # 获取港股K线数据
    # frequency: 9=日K线
    bars = client.bars(frequency=9, market=47, symbol='00700', start=0, offset=100)
    print("\n腾讯控股(00700)日K线:")
    print(bars)
