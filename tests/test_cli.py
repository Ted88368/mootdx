"""Tests for mootdx2 CLI commands using pytest fixtures and click.testing.CliRunner."""
from unittest import mock

import pytest
from mootdx2.__main__ import entry


class TestEntry:
    """Tests for the root CLI group (entry)."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['--help'])
        assert result.exit_code == 0
        assert 'Commands:' in result.output
        assert 'quotes' in result.output
        assert 'reader' in result.output
        assert 'bestip' in result.output
        assert 'affair' in result.output
        assert 'bundle' in result.output

    def test_version(self, cli_runner):
        from mootdx2 import __version__
        result = cli_runner.invoke(entry, ['--version'])
        assert result.exit_code == 0
        assert f'v{__version__}' in result.output

    def test_no_args_shows_commands(self, cli_runner):
        result = cli_runner.invoke(entry)
        assert result.exit_code == 2
        assert 'Commands:' in result.output


class TestQuotesCommand:
    """Tests for the `quotes` subcommand."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['quotes', '--help'])
        assert result.exit_code == 0
        assert '--symbol' in result.output
        assert '--action' in result.output
        assert '--market' in result.output
        assert '--output' in result.output

    def test_default_options(self, cli_runner, mock_quotes):
        mock_quotes_class, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['quotes'])
        assert result.exit_code == 0
        mock_quotes_class.factory.assert_called_once_with(market='std', multithread=True)
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=9)

    def test_custom_symbol_action_market(self, cli_runner, mock_quotes):
        mock_quotes_class, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['quotes', '-s', '000001', '-a', 'minute', '-m', 'ext'])
        assert result.exit_code == 0
        mock_quotes_class.factory.assert_called_once_with(market='ext', multithread=True)
        mock_client.bars.assert_called_once_with(symbol='000001', frequency=8)

    def test_with_output_file(self, cli_runner, mock_quotes, mock_to_file):
        result = cli_runner.invoke(entry, ['quotes', '-o', 'output.csv'])
        assert result.exit_code == 0
        mock_to_file.assert_called_once()

    def test_daily_action(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['quotes', '-a', 'daily'])
        assert result.exit_code == 0
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=9)

    def test_fzline_action(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['quotes', '-a', 'fzline'])
        assert result.exit_code == 0
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=0)


class TestReaderCommand:
    """Tests for the `reader` subcommand."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['reader', '--help'])
        assert result.exit_code == 0
        assert '--tdxdir' in result.output
        assert '--symbol' in result.output
        assert '--action' in result.output
        assert '--market' in result.output
        assert '--output' in result.output

    def test_default_options(self, cli_runner, mock_reader):
        mock_reader_class, mock_client = mock_reader
        result = cli_runner.invoke(entry, ['reader'])
        assert result.exit_code == 0
        mock_reader_class.factory.assert_called_once_with(market='std', tdxdir='C:/new_tdx')
        mock_client.daily.assert_called_once_with(symbol='600000')

    def test_custom_options(self, cli_runner, mock_reader):
        mock_reader_class, mock_client = mock_reader
        result = cli_runner.invoke(entry, ['reader', '-s', '000001', '-a', 'minute', '-m', 'ext', '-d', '/tmp/tdx'])
        assert result.exit_code == 0
        mock_reader_class.factory.assert_called_once_with(market='ext', tdxdir='/tmp/tdx')
        mock_client.minute.assert_called_once_with(symbol='000001')

    def test_with_output_file(self, cli_runner, mock_reader, mock_to_file):
        result = cli_runner.invoke(entry, ['reader', '-o', 'output.h5'])
        assert result.exit_code == 0
        mock_to_file.assert_called_once()


class TestBestipCommand:
    """Tests for the `bestip` subcommand (server)."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['bestip', '--help'])
        assert result.exit_code == 0
        assert '--limit' in result.output
        assert '--verbose' in result.output

    def test_default_options(self, cli_runner, mock_bestip):
        result = cli_runner.invoke(entry, ['bestip'])
        assert result.exit_code == 0
        mock_bestip.assert_called_once_with(limit=5, console=True, sync=False)

    def test_custom_limit(self, cli_runner, mock_bestip):
        result = cli_runner.invoke(entry, ['bestip', '-l', '10'])
        assert result.exit_code == 0
        mock_bestip.assert_called_once_with(limit=10, console=True, sync=False)

    def test_verbose_flag(self, cli_runner, mock_bestip):
        result = cli_runner.invoke(entry, ['bestip', '-v'])
        assert result.exit_code == 0
        mock_bestip.assert_called_once_with(limit=5, console=True, sync=False)


class TestAffairCommand:
    """Tests for the `affair` subcommand."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['affair', '--help'])
        assert result.exit_code == 0
        assert '--parse' in result.output
        assert '--fetch' in result.output
        assert '--downall' in result.output
        assert '--downdir' in result.output
        assert '--listfile' in result.output

    def test_listfile(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '-l'])
        assert result.exit_code == 0
        assert 'gpcw20240630.zip' in result.output
        assert 'abc123' in result.output
        assert 'gpcw20231231.zip' in result.output

    def test_listfile_verbose(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '--listfile', '-v'])
        assert result.exit_code == 0
        assert 'gpcw20240630.zip' in result.output

    def test_download_all(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '-a'])
        assert result.exit_code == 0
        mock_affair.fetch.assert_called_once_with(downdir='output')

    def test_fetch_single_file(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '-f', 'gpcw20240630.zip'])
        assert result.exit_code == 0
        mock_affair.fetch.assert_called_once_with(downdir='output', filename='gpcw20240630.zip')

    def test_fetch_with_custom_dir(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '-f', 'gpcw20240630', '-d', '/tmp/finance'])
        assert result.exit_code == 0
        mock_affair.fetch.assert_called_once_with(downdir='/tmp/finance', filename='gpcw20240630.zip')

    def test_parse_existing_file(self, cli_runner, mock_affair, sample_df):
        mock_affair.parse.return_value = sample_df
        result = cli_runner.invoke(entry, ['affair', '-p', 'gpcw20240630'])
        assert result.exit_code == 0
        mock_affair.parse.assert_called_once()

    def test_parse_missing_file(self, cli_runner, mock_affair):
        result = cli_runner.invoke(entry, ['affair', '-p', 'nonexistent.zip'])
        assert result.exit_code == 0


class TestBundleCommand:
    """Tests for the `bundle` subcommand."""

    def test_help(self, cli_runner):
        result = cli_runner.invoke(entry, ['bundle', '--help'])
        assert result.exit_code == 0
        assert '--output' in result.output
        assert '--symbol' in result.output
        assert '--action' in result.output
        assert '--extension' in result.output

    def test_single_symbol(self, cli_runner, mock_quotes):
        mock_quotes_class, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['bundle'])
        assert result.exit_code == 0
        mock_quotes_class.factory.assert_called_once_with(market='std', multithread=True)
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=9)

    def test_multiple_symbols(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['bundle', '-s', '600000,000001,000002'])
        assert result.exit_code == 0
        assert mock_client.bars.call_count == 3

    def test_custom_output_and_extension(self, cli_runner, mock_quotes, mock_to_file):
        result = cli_runner.invoke(entry, ['bundle', '-o', '/tmp/bundle', '-e', 'h5'])
        assert result.exit_code == 0

    def test_minute_action(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['bundle', '-a', 'minute'])
        assert result.exit_code == 0
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=8)

    def test_fzline_action(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['bundle', '-a', 'fzline'])
        assert result.exit_code == 0
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=0)

    def test_ext_market(self, cli_runner, mock_quotes):
        mock_quotes_class, _ = mock_quotes
        result = cli_runner.invoke(entry, ['bundle', '-m', 'ext'])
        assert result.exit_code == 0
        mock_quotes_class.factory.assert_called_once_with(market='ext', multithread=True)

    def test_daily_action(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        result = cli_runner.invoke(entry, ['bundle', '-a', 'daily'])
        assert result.exit_code == 0
        mock_client.bars.assert_called_once_with(symbol='600000', frequency=9)


class TestErrorHandling:
    """Tests for error propagation in CLI commands (fixture-based)."""

    def test_quotes_client_error(self, cli_runner, mock_quotes):
        mock_quotes_class, _ = mock_quotes
        mock_quotes_class.factory.side_effect = RuntimeError('Connection failed')
        result = cli_runner.invoke(entry, ['quotes', '-s', '000001'])
        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)

    def test_quotes_bars_error(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        mock_client.bars.side_effect = ValueError('Invalid symbol')
        result = cli_runner.invoke(entry, ['quotes', '-s', 'INVALID'])
        assert result.exit_code != 0
        assert isinstance(result.exception, ValueError)

    def test_reader_client_error(self, cli_runner, mock_reader):
        mock_reader_class, _ = mock_reader
        mock_reader_class.factory.side_effect = RuntimeError('Cannot access TDX directory')
        result = cli_runner.invoke(entry, ['reader', '-s', '000001'])
        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)

    def test_reader_method_error(self, cli_runner, mock_reader):
        _, mock_client = mock_reader
        mock_client.daily.side_effect = FileNotFoundError('TDX data not found')
        result = cli_runner.invoke(entry, ['reader', '-s', '000001'])
        assert result.exit_code != 0
        assert isinstance(result.exception, FileNotFoundError)

    def test_bundle_client_error(self, cli_runner, mock_quotes):
        mock_quotes_class, _ = mock_quotes
        mock_quotes_class.factory.side_effect = RuntimeError('Connection failed')
        result = cli_runner.invoke(entry, ['bundle', '-s', '600000'])
        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)

    def test_bundle_bars_error(self, cli_runner, mock_quotes):
        _, mock_client = mock_quotes
        mock_client.bars.side_effect = RuntimeError('Download failed')
        result = cli_runner.invoke(entry, ['bundle', '-s', '600000'])
        assert result.exit_code != 0
        assert isinstance(result.exception, RuntimeError)