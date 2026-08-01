from abc import ABC
from pathlib import Path

from tdxpy.reader import TdxExHqDailyBarReader
from tdxpy.reader import TdxLCMinBarReader
from tdxpy.reader import TdxMinBarReader

from mootdx2.consts import DEFAULT_TDXDIR
from mootdx2.contrib.compat import MooTdxDailyBarReader
from mootdx2.utils import get_stock_market
from mootdx2.utils import to_data


class Reader(object):
    @staticmethod
    def factory(market='std', **kwargs):
        """
        Reader 工厂方法

        :param market: std 标准市场, ext 扩展市场
        :param kwargs: 可变参数
        :return:
        """

        if market == 'ext':
            return ExtReader(**kwargs)

        return StdReader(**kwargs)


class ReaderBase(ABC):
    # 默认通达信安装目录 (按平台惯例: Windows C:/new_tdx, macOS ~/new_tdx, Linux ~/.local/share/new_tdx)
    tdxdir = DEFAULT_TDXDIR

    def __init__(self, tdxdir=None):
        """
        构造函数

        :param tdxdir: 通达信安装目录, 默认按平台惯例 (见 DEFAULT_TDXDIR)
        """

        if tdxdir is None:
            tdxdir = DEFAULT_TDXDIR

        if not Path(tdxdir).is_dir():
            raise Exception(f'tdxdir 目录不存在: {tdxdir}')

        self.tdxdir = tdxdir

    def find_path(self, symbol=None, subdir='lday', suffix=None, **kwargs):
        """
        自动匹配文件路径，辅助函数

        :param symbol:
        :param subdir:
        :param suffix:
        :return: pd.dataFrame or None
        """

        # 判断市场, 带#扩展市场
        if '#' in symbol:
            market = 'ds'
        # 通达信特有的板块指数88****开头的日线数据放在 sh 文件夹下
        elif symbol.startswith('88'):
            market = 'sh'
        else:
            # 判断是sh还是sz
            market = get_stock_market(symbol, True)

        # 判断前缀(市场是sh和sz重置前缀)
        if market.lower() in ['sh', 'sz']:
            symbol = market + symbol.lower().replace(market, '')

        # 判断后缀
        suffix = suffix if isinstance(suffix, list) else [suffix]

        # 调试使用
        if kwargs.get('debug'):
            return market, symbol, suffix

        # 遍历扩展名
        for ex_ in suffix:
            ex_ = ex_.strip('.')
            vipdoc = Path(self.tdxdir) / 'vipdoc' / market / subdir / f'{symbol}.{ex_}'

            if Path(vipdoc).exists():
                return vipdoc

        return None


class StdReader(ReaderBase):
    """股票市场"""

    def daily(self, symbol=None, **kwargs):
        """
        获取日线数据

        :param symbol: 证券代码
        :return: pd.dataFrame or None
        """
        symbol = Path(symbol).stem
        reader = MooTdxDailyBarReader()
        vipdoc = self.find_path(symbol=symbol, subdir='lday', suffix='day')

        result = reader.get_df(str(vipdoc)) if vipdoc else None
        return to_data(result, symbol=symbol, **kwargs)

    def minute(self, symbol=None, suffix=1, **kwargs):  # noqa
        """
        获取1, 5分钟线

        :param suffix: 文件前缀
        :param symbol: 证券代码
        :return: pd.dataFrame or None
        """
        symbol = Path(symbol).stem
        subdir = 'fzline' if str(suffix) == '5' else 'minline'
        suffix = ['lc5', '5'] if str(suffix) == '5' else ['lc1', '1']
        symbol = self.find_path(symbol, subdir=subdir, suffix=suffix)

        if symbol is not None:
            reader = TdxMinBarReader() if 'lc' not in symbol.suffix else TdxLCMinBarReader()
            return reader.get_df(str(symbol))

        return None

    def fzline(self, symbol=None):
        """
        分钟线数据

        :param symbol: 自定义板块股票列表, 类型 list
        :return: pd.dataFrame or Bool
        """
        return self.minute(symbol, suffix=5)

    def xdxr(self, symbol='', **kwargs):
        """
        读取除权除息信息（本地缓存优先，在线回退）

        本地 gbbq 文件为加密格式（密钥硬编码在 tdxw.exe 内，公开 Python 解密实现不存在），
        因此复用 ``mootdx2.utils.adjust.get_xdxr()`` 的 24h pickle 缓存
        (``~/.mootdx2/xdxr/{symbol}.plk``)。缓存命中即纯离线读取；未命中或过期则
        联网拉取并写回缓存。返回 schema 与 ``StdQuotes.xdxr()`` 一致。

        :param symbol: 证券代码
        :return: pd.DataFrame, 列含 year/month/day/category/name/fenhong/peigujia/
                 songzhuangu/peigu/suogu/.../code，索引为 date (DatetimeIndex)
        """
        from mootdx2.utils.adjust import get_xdxr

        symbol = Path(symbol).stem if symbol else ''
        return get_xdxr(symbol)

    def block_new(self, name: str = None, symbol: list = None, group=False, **kwargs):
        """
        自定义板块数据操作

        :param name: 自定义板块名称
        :param symbol: 自定义板块股票列表, 类型 list
        :param group:
        :return: pd.dataFrame or Bool
        """
        from mootdx2.tools.customize import Customize

        reader = Customize(tdxdir=self.tdxdir)

        if symbol:
            return reader.create(name=name, symbol=symbol, **kwargs)

        return reader.search(name=name, group=group)

    def block(self, symbol='', group=False, **kwargs):
        """
        获取板块数据

        :param symbol:  板块文件
        :param group:   分组解析
        :return: pd.dataFrame or None
        """
        # from mootdx2.block import BlockParse
        from mootdx2.parse import BaseParse

        return BaseParse(self.tdxdir).parse(symbol, group=group, **kwargs)


class ExtReader(ReaderBase):
    """扩展市场读取"""

    def __init__(self, tdxdir=None):
        super(ExtReader, self).__init__(tdxdir)
        self.reader = TdxExHqDailyBarReader()

    def daily(self, symbol=None):
        """
        获取扩展市场日线数据

        :return: pd.dataFrame or None
        """

        vipdoc = self.find_path(symbol=symbol, subdir='lday', suffix='day')
        return self.reader.get_df(str(vipdoc)) if vipdoc else None

    def minute(self, symbol=None):
        """
        获取扩展市场分钟线数据

        :return: pd.dataFrame or None
        """

        if not symbol:
            return None

        vipdoc = self.find_path(symbol=symbol, subdir='minline', suffix=['lc1', '1'])
        return self.reader.get_df(str(vipdoc)) if vipdoc else None

    def fzline(self, symbol=None):
        """
        获取日线数据

        :return: pd.dataFrame or None
        """

        vipdoc = self.find_path(symbol=symbol, subdir='fzline', suffix='lc5')
        return self.reader.get_df(str(vipdoc)) if symbol else None
