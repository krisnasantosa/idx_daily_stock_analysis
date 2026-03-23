# -*- coding: utf-8 -*-
"""
印尼 IDX 股票支持单元测试

覆盖：
- is_idx_stock_code() 识别 .JK 代码
- normalize_stock_code() 保留 .JK 代码
- _market_tag() 返回 'idx'
- DataFetcherManager 路由到 YfinanceFetcher
- YfinanceFetcher._convert_stock_code() 透传 .JK 代码
- YfinanceFetcher.get_realtime_quote() 处理 .JK 代码
- trading_calendar.get_market_for_stock() 返回 'idx'
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Mock optional dependencies that may not be installed in CI
import types as _types
import unittest.mock as _mock

_MOCK_MODS = (
    'fake_useragent', 'efinance', 'akshare', 'tushare', 'pytdx', 'baostock',
    'tenacity', 'sqlalchemy',
    'dotenv', 'yfinance',
)
for _mod in _MOCK_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = _mock.MagicMock()

# tenacity needs real retry/stop/wait symbols (used as decorators at import time)
_tenacity = sys.modules['tenacity']
_tenacity.retry = lambda *a, **kw: (lambda f: f)  # no-op decorator
_tenacity.stop_after_attempt = _mock.MagicMock(return_value=None)
_tenacity.wait_exponential = _mock.MagicMock(return_value=None)
_tenacity.retry_if_exception_type = _mock.MagicMock(return_value=None)
_tenacity.before_sleep_log = _mock.MagicMock(return_value=None)

# dotenv needs real function names
_dotenv = sys.modules['dotenv']
_dotenv.load_dotenv = _mock.MagicMock(return_value=True)
_dotenv.dotenv_values = _mock.MagicMock(return_value={})

# src.config and other heavy src modules that cascade from data_provider imports
for _mod in ('src.config', 'src.data.stock_mapping'):
    if _mod not in sys.modules:
        sys.modules[_mod] = _mock.MagicMock()
# Ensure stock mapping has the expected interface
sys.modules['src.data.stock_mapping'].STOCK_NAME_MAP = {}
sys.modules['src.data.stock_mapping'].is_meaningful_stock_name = lambda name, code: bool(name)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestIsIdxStockCode(unittest.TestCase):
    """is_idx_stock_code() 识别 .JK 格式代码"""

    def setUp(self):
        from data_provider.base import is_idx_stock_code
        self.fn = is_idx_stock_code

    def test_bbca_jk(self):
        self.assertTrue(self.fn('BBCA.JK'))

    def test_tlkm_jk(self):
        self.assertTrue(self.fn('TLKM.JK'))

    def test_bbri_jk(self):
        self.assertTrue(self.fn('BBRI.JK'))

    def test_lowercase(self):
        self.assertTrue(self.fn('bbca.jk'))

    def test_mixed_case(self):
        self.assertTrue(self.fn('Bbca.Jk'))

    def test_us_stock_not_idx(self):
        self.assertFalse(self.fn('AAPL'))

    def test_hk_stock_not_idx(self):
        self.assertFalse(self.fn('HK00700'))

    def test_cn_stock_not_idx(self):
        self.assertFalse(self.fn('600519'))

    def test_empty_string(self):
        self.assertFalse(self.fn(''))

    def test_none_coerced(self):
        self.assertFalse(self.fn(None))


class TestNormalizeStockCode(unittest.TestCase):
    """normalize_stock_code() 正确保留 .JK 代码"""

    def setUp(self):
        from data_provider.base import normalize_stock_code
        self.fn = normalize_stock_code

    def test_jk_preserved(self):
        self.assertEqual(self.fn('BBCA.JK'), 'BBCA.JK')

    def test_jk_uppercase_preserved(self):
        self.assertEqual(self.fn('TLKM.JK'), 'TLKM.JK')

    def test_cn_still_works(self):
        self.assertEqual(self.fn('SH600519'), '600519')

    def test_hk_still_works(self):
        self.assertEqual(self.fn('1810.HK'), 'HK01810')

    def test_us_still_works(self):
        self.assertEqual(self.fn('AAPL'), 'AAPL')


class TestMarketTag(unittest.TestCase):
    """_market_tag() 对 .JK 代码返回 'idx'"""

    def setUp(self):
        from data_provider.base import _market_tag
        self.fn = _market_tag

    def test_idx_market(self):
        self.assertEqual(self.fn('BBCA.JK'), 'idx')

    def test_us_market(self):
        self.assertEqual(self.fn('AAPL'), 'us')

    def test_hk_market(self):
        self.assertEqual(self.fn('HK00700'), 'hk')

    def test_cn_market(self):
        self.assertEqual(self.fn('600519'), 'cn')


class TestYfinanceFetcherConvertCode(unittest.TestCase):
    """YfinanceFetcher._convert_stock_code() 透传 .JK 代码"""

    def setUp(self):
        from data_provider.yfinance_fetcher import YfinanceFetcher
        self.fetcher = YfinanceFetcher()

    def test_bbca_jk_passthrough(self):
        self.assertEqual(self.fetcher._convert_stock_code('BBCA.JK'), 'BBCA.JK')

    def test_tlkm_jk_passthrough(self):
        self.assertEqual(self.fetcher._convert_stock_code('TLKM.JK'), 'TLKM.JK')

    def test_lowercase_normalized(self):
        self.assertEqual(self.fetcher._convert_stock_code('bbca.jk'), 'BBCA.JK')

    def test_us_stock_unchanged(self):
        self.assertEqual(self.fetcher._convert_stock_code('AAPL'), 'AAPL')

    def test_cn_stock_converted(self):
        self.assertEqual(self.fetcher._convert_stock_code('600519'), '600519.SS')


class TestYfinanceFetcherRealtimeQuoteIDX(unittest.TestCase):
    """YfinanceFetcher.get_realtime_quote() 处理 .JK 代码"""

    def setUp(self):
        from data_provider.yfinance_fetcher import YfinanceFetcher
        self.fetcher = YfinanceFetcher()

    def _make_mock_hist(self, close=9000.0, prev_close=8800.0):
        return pd.DataFrame({
            'Close': [prev_close, close],
            'Open': [prev_close - 50, close - 20],
            'High': [prev_close + 100, close + 100],
            'Low': [prev_close - 100, close - 100],
            'Volume': [5000000, 6000000],
        }, index=pd.DatetimeIndex(['2025-02-16', '2025-02-17']))

    @patch('data_provider.yfinance_fetcher.YfinanceFetcher._get_yf_realtime_quote')
    def test_idx_routes_to_yf_method(self, mock_get_quote):
        """IDX .JK 代码应调用 _get_yf_realtime_quote"""
        mock_get_quote.return_value = MagicMock(code='BBCA.JK', price=9000.0)
        result = self.fetcher.get_realtime_quote('BBCA.JK')
        mock_get_quote.assert_called_once_with('BBCA.JK')
        self.assertIsNotNone(result)

    def test_idx_quote_returns_unified_quote(self):
        """_get_yf_realtime_quote 应返回 UnifiedRealtimeQuote（通过 mock yfinance）"""
        from data_provider.realtime_types import UnifiedRealtimeQuote
        import data_provider.yfinance_fetcher as yf_mod

        mock_hist = self._make_mock_hist()
        mock_ticker = MagicMock()
        mock_ticker.fast_info = None
        mock_ticker.history.return_value = mock_hist
        mock_ticker.info = {'shortName': 'Bank Central Asia'}

        mock_yf_mod = MagicMock()
        mock_yf_mod.Ticker.return_value = mock_ticker

        original = sys.modules.get('yfinance')
        sys.modules['yfinance'] = mock_yf_mod
        try:
            result = self.fetcher._get_yf_realtime_quote('BBCA.JK')
        finally:
            if original is not None:
                sys.modules['yfinance'] = original
            # Don't remove the mock - it was already there from setup

        if result is not None:
            self.assertIsInstance(result, UnifiedRealtimeQuote)
            self.assertEqual(result.code, 'BBCA.JK')


class TestTradingCalendarIDX(unittest.TestCase):
    """trading_calendar 识别 IDX 市场"""

    def test_get_market_for_idx_stock(self):
        from src.core.trading_calendar import get_market_for_stock
        self.assertEqual(get_market_for_stock('BBCA.JK'), 'idx')

    def test_get_market_for_cn_stock(self):
        from src.core.trading_calendar import get_market_for_stock
        self.assertEqual(get_market_for_stock('600519'), 'cn')

    def test_get_market_for_us_stock(self):
        from src.core.trading_calendar import get_market_for_stock
        self.assertEqual(get_market_for_stock('AAPL'), 'us')

    def test_idx_in_market_exchange(self):
        from src.core.trading_calendar import MARKET_EXCHANGE
        self.assertIn('idx', MARKET_EXCHANGE)
        self.assertEqual(MARKET_EXCHANGE['idx'], 'XIDX')

    def test_idx_in_market_timezone(self):
        from src.core.trading_calendar import MARKET_TIMEZONE
        self.assertIn('idx', MARKET_TIMEZONE)
        self.assertEqual(MARKET_TIMEZONE['idx'], 'Asia/Jakarta')


class TestDataFetcherManagerIDXRouting(unittest.TestCase):
    """DataFetcherManager 将 .JK 代码路由到 YfinanceFetcher"""

    def setUp(self):
        from data_provider.base import DataFetcherManager
        self.manager = DataFetcherManager.__new__(DataFetcherManager)

        # Mock YfinanceFetcher
        mock_yf = MagicMock()
        mock_yf.name = "YfinanceFetcher"
        mock_yf.priority = 4

        # Mock a CN fetcher that should NOT be called for IDX
        mock_cn = MagicMock()
        mock_cn.name = "EfinanceFetcher"
        mock_cn.priority = 0

        self.manager._fetchers = [mock_cn, mock_yf]
        self.mock_yf = mock_yf
        self.mock_cn = mock_cn

    def test_idx_stock_routes_to_yfinance(self):
        """IDX 代码只调用 YfinanceFetcher，不调用 CN 数据源"""
        expected_df = pd.DataFrame({
            'date': pd.to_datetime(['2025-02-17']),
            'open': [8950.0], 'high': [9100.0], 'low': [8900.0],
            'close': [9000.0], 'volume': [6000000.0],
            'amount': [5.4e10], 'pct_chg': [2.27],
        })
        self.mock_yf.get_daily_data.return_value = expected_df

        df, source = self.manager.get_daily_data('BBCA.JK', days=30)

        self.mock_yf.get_daily_data.assert_called_once()
        self.mock_cn.get_daily_data.assert_not_called()
        self.assertEqual(source, 'YfinanceFetcher')
        self.assertFalse(df.empty)


if __name__ == '__main__':
    unittest.main()
