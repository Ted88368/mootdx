import pandas as pd
import pytest

from mootdx2.reader import Reader


@pytest.fixture
def reader():
    return Reader.factory(market='std', tdxdir='tests/fixtures')


def test_xdxr_returns_dataframe(reader):
    """StdReader.xdxr() 返回与 StdQuotes.xdxr() 同 schema 的 DataFrame"""
    xdxr = reader.xdxr(symbol='600000')

    assert xdxr.empty is False
    # 与 StdQuotes.xdxr() + get_xdxr() 后处理一致的 schema
    assert 'code' in xdxr.columns
    assert 'category' in xdxr.columns
    assert 'fenhong' in xdxr.columns
    assert 'peigu' in xdxr.columns
    assert 'peigujia' in xdxr.columns
    assert 'songzhuangu' in xdxr.columns
    # reversion._reversion() 用 bfq_data.index 切片 xdxr，要求 DatetimeIndex
    assert isinstance(xdxr.index, pd.DatetimeIndex)


def test_xdxr_symbol_normalization(reader):
    """带扩展名/路径的 symbol 应被规范化为纯代码"""
    xdxr = reader.xdxr(symbol='600000.day')

    assert xdxr.empty is False
    if 'code' in xdxr.columns:
        assert (xdxr['code'] == '600000').all()
