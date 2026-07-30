import unittest.mock
import pandas
import pytest
from click.testing import CliRunner

from mootdx2.quotes import Quotes


def is_empty(obj):
    if isinstance(obj, pandas.DataFrame):
        return obj.empty

    return not obj


@pytest.fixture()
def quotes():
    return Quotes.factory('std')

# @pytest.fixture()
# def reader():
#     return Reader.factory("std")


# ---------------------------------------------------------------------------
# CLI test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cli_runner():
    """Click test runner for CLI commands."""
    return CliRunner()


@pytest.fixture
def sample_df():
    """Reusable sample DataFrame for mocked returns."""
    return pandas.DataFrame({
        'open': [10.0], 'close': [10.5], 'high': [11.0], 'low': [9.8], 'volume': [1000]
    })


def _make_client(bars_return=None, daily_return=None, minute_return=None):
    """Build a generic mock client with optional return values."""
    client = unittest.mock.MagicMock()
    client.bars.return_value = bars_return
    client.daily.return_value = daily_return
    client.minute.return_value = minute_return
    return client


@pytest.fixture
def mock_quotes(sample_df):
    """Patch mootdx2.quotes.Quotes with a pre-configured mock client."""
    with unittest.mock.patch('mootdx2.quotes.Quotes') as mock_class:
        client = _make_client(bars_return=sample_df)
        mock_class.factory.return_value = client
        yield mock_class, client


@pytest.fixture
def mock_reader(sample_df):
    """Patch mootdx2.reader.Reader with a pre-configured mock client."""
    with unittest.mock.patch('mootdx2.reader.Reader') as mock_class:
        client = _make_client(daily_return=sample_df, minute_return=sample_df)
        mock_class.factory.return_value = client
        yield mock_class, client


@pytest.fixture
def mock_bestip():
    """Patch mootdx2.server.bestip."""
    with unittest.mock.patch('mootdx2.server.bestip') as m:
        yield m


@pytest.fixture
def mock_affair():
    """Patch mootdx2.affair.Affair with sample file listing."""
    with unittest.mock.patch('mootdx2.affair.Affair') as m:
        m.files.return_value = [
            {'filename': 'gpcw20240630.zip', 'filesize': '1024', 'hash': 'abc123'},
            {'filename': 'gpcw20231231.zip', 'filesize': '2048', 'hash': 'def456'},
        ]
        yield m


@pytest.fixture
def mock_to_file():
    """Patch mootdx2.__main__.to_file."""
    with unittest.mock.patch('mootdx2.__main__.to_file') as m:
        yield m
