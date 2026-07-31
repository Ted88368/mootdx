import httpx
import pandas as pd

from mootdx2.cache import file_cache
from mootdx2.logger import logger
from mootdx2.utils import get_config_path
from mootdx2.utils import get_stock_market


def fq_factor(symbol: str, method: str, ) -> pd.DataFrame:
    symbol = symbol.replace('sh', '').replace('sz', '').replace('bj', '')
    market = get_stock_market(symbol, string=True)
    symbol = f'{market}{symbol}'
    cache_file = get_config_path(f'caches/factor/{symbol}.plk')

    @file_cache(filepath=cache_file, refresh_time=3600 * 24)
    def _factor(symbol: str, method: str, ) -> pd.DataFrame:

        import json

        try:
            url = 'https://finance.sina.com.cn/realstock/company/{}/{}.js'
            rsp = httpx.get(url.format(symbol, method))
            rsp_data = json.loads(rsp.text.split('=')[1].split('\n')[0])
        except (SyntaxError, httpx.ConnectError) as ex:
            logger.error(ex)
            return pd.DataFrame(None)

        records = rsp_data.get('data', [])
        if len(records) == 0:
            raise ValueError(f'sina {method} factor not available')

        # ETFs return 4 fields ['d','f','s','u'], stocks return ['d','f']
        # For ETFs, 's' is the actual factor value; 'f' is just a flag
        factor_key = 's' if 's' in records[0] else 'f'

        res = pd.DataFrame(records)[['d', factor_key]]
        res.columns = ['date', 'factor']
        res.date = pd.to_datetime(res.date)

        res.set_index('date', inplace=True)
        return res

    return _factor(symbol, method)


if __name__ == '__main__':
    fq = fq_factor('600036', 'qfq')
    print(fq)
