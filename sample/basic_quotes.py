from mootdx.quotes import Quotes

client = Quotes.factory(market="std", quiet=True)  # 标准市场
# client = Quotes.factory(market='ext', multithread=True, heartbeat=True) # 扩展市场

# quote = client.bars(symbol='600036', frequency=9, offset=10)
# print(quote)
#
# quote = client.index(symbol='000001', frequency=9)
# print(quote)
#
# quote = client.minute(symbol='000001')
# print(quote)

# client = Quotes.factory(market='std')
# from mootdx.logger import logger, logger
#
# # logger.remove()
#
# logger.info("------------")
# logger.info("-========")
#
# # rd = client.minutes('159995', '20200130')  # 这条记录不存在为啥会报异常？返回None就好了吧
# rd = client.minutes("300191", "301188")  # 这条记录不存在为啥会报异常？返回None就好了吧
#
# print(rd)
if __name__ == '__main__':
    # 获取K线数据 (不复权)
    df = client.bars(symbol='600036', frequency=9, start=0, offset=100)
    print("不复权数据:")
    print(df.tail())
    
    # 如果需要复权数据，可以使用 reversion 函数
    # from mootdx.tools.reversion import reversion
    # xdxr_data = client.xdxr(symbol='600036')
    # df['code'] = '600036'
    # qfq_df = reversion(df, xdxr_data, '01')  # '01' 表示前复权
    # print("\n前复权数据:")
    # print(qfq_df.head())
