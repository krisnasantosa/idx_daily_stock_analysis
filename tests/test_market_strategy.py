# -*- coding: utf-8 -*-
"""Tests for market strategy blueprints."""

import unittest

from src.core.market_strategy import get_market_strategy_blueprint
from src.market_analyzer import MarketAnalyzer, MarketOverview


class TestMarketStrategyBlueprint(unittest.TestCase):
    """Validate CN/US/IDX strategy blueprint basics."""

    def test_cn_blueprint_contains_action_framework(self):
        blueprint = get_market_strategy_blueprint("cn")
        block = blueprint.to_prompt_block()

        self.assertIn("A股市场三段式复盘策略", block)
        self.assertIn("Action Framework", block)
        self.assertIn("进攻", block)

    def test_us_blueprint_contains_regime_strategy(self):
        blueprint = get_market_strategy_blueprint("us")
        block = blueprint.to_prompt_block()

        self.assertIn("US Market Regime Strategy", block)
        self.assertIn("Risk-on", block)
        self.assertIn("Macro & Flows", block)

    def test_idx_blueprint_contains_ihsg_strategy(self):
        blueprint = get_market_strategy_blueprint("id")
        block = blueprint.to_prompt_block()

        self.assertIn("IDX Indonesia Market Strategy", block)
        self.assertIn("Risk-on", block)
        self.assertIn("Macro & Flows", block)
        self.assertIn("IHSG", block)

    def test_idx_alias_returns_same_blueprint(self):
        """'idx' alias resolves to same IDX_BLUEPRINT as 'id'."""
        blueprint_id = get_market_strategy_blueprint("id")
        blueprint_idx = get_market_strategy_blueprint("idx")
        self.assertEqual(blueprint_id.region, blueprint_idx.region)
        self.assertEqual(blueprint_id.title, blueprint_idx.title)

    def test_unknown_region_falls_back_to_cn(self):
        blueprint = get_market_strategy_blueprint("unknown")
        self.assertEqual(blueprint.region, "cn")


class TestMarketAnalyzerStrategyPrompt(unittest.TestCase):
    """Validate strategy section is injected into prompt/report."""

    def test_cn_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="cn")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("策略计划", prompt)
        self.assertIn("A股市场三段式复盘策略", prompt)

    def test_us_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="us")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("Strategy Plan", prompt)
        self.assertIn("US Market Regime Strategy", prompt)

    def test_idx_prompt_contains_strategy_plan_section(self):
        analyzer = MarketAnalyzer(region="id")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("Strategy Plan", prompt)
        self.assertIn("IDX Indonesia Market Strategy", prompt)
        self.assertIn("IDX Market Recap", prompt)

    def test_idx_prompt_contains_index_hint(self):
        analyzer = MarketAnalyzer(region="id")
        prompt = analyzer._build_review_prompt(MarketOverview(date="2026-02-24"), [])

        self.assertIn("IHSG", prompt)


class TestIDXMarketAnalyzerInit(unittest.TestCase):
    """Validate MarketAnalyzer initializes correctly for IDX region."""

    def test_region_id_accepted(self):
        analyzer = MarketAnalyzer(region="id")
        self.assertEqual(analyzer.region, "id")

    def test_region_unknown_falls_back_to_cn(self):
        analyzer = MarketAnalyzer(region="xyz")
        self.assertEqual(analyzer.region, "cn")

    def test_idx_profile_has_correct_mood_code(self):
        from src.core.market_profile import get_profile
        profile = get_profile("id")
        self.assertEqual(profile.mood_index_code, "^JKSE")
        self.assertEqual(profile.region, "id")

    def test_idx_profile_alias_idx_resolves(self):
        from src.core.market_profile import get_profile
        profile = get_profile("idx")
        self.assertEqual(profile.region, "id")

    def test_idx_profile_no_market_stats(self):
        from src.core.market_profile import get_profile
        profile = get_profile("id")
        self.assertFalse(profile.has_market_stats)
        self.assertFalse(profile.has_sector_rankings)

    def test_idx_profile_has_news_queries(self):
        from src.core.market_profile import get_profile
        profile = get_profile("id")
        self.assertTrue(len(profile.news_queries) > 0)
        # At least one query should reference Indonesia/IDX
        combined = " ".join(profile.news_queries).lower()
        self.assertTrue("ihsg" in combined or "indonesia" in combined or "idx" in combined)


class TestIDXTemplateReview(unittest.TestCase):
    """Validate template report generation for IDX region."""

    def test_idx_template_review_contains_english_recap(self):
        from src.market_analyzer import MarketIndex

        analyzer = MarketAnalyzer(region="id")
        overview = MarketOverview(
            date="2026-03-23",
            indices=[
                MarketIndex(
                    code="^JKSE",
                    name="IHSG",
                    current=7300.0,
                    change=50.0,
                    change_pct=0.69,
                )
            ],
        )
        report = analyzer._generate_template_review(overview, [])
        self.assertIn("IDX Market Recap", report)
        self.assertIn("IHSG", report)
        self.assertIn("rising", report)

    def test_idx_template_review_declining_market(self):
        from src.market_analyzer import MarketIndex

        analyzer = MarketAnalyzer(region="id")
        overview = MarketOverview(
            date="2026-03-23",
            indices=[
                MarketIndex(
                    code="^JKSE",
                    name="IHSG",
                    current=7200.0,
                    change=-150.0,
                    change_pct=-2.04,
                )
            ],
        )
        report = analyzer._generate_template_review(overview, [])
        self.assertIn("declining", report)


class TestIDXComputeEffectiveRegion(unittest.TestCase):
    """Validate compute_effective_region handles 'id' region."""

    def test_id_region_open(self):
        from src.core.trading_calendar import compute_effective_region
        result = compute_effective_region("id", {"idx", "cn"})
        self.assertEqual(result, "id")

    def test_id_region_closed(self):
        from src.core.trading_calendar import compute_effective_region
        result = compute_effective_region("id", {"cn", "us"})
        self.assertEqual(result, "")

    def test_id_region_only_idx_open(self):
        from src.core.trading_calendar import compute_effective_region
        result = compute_effective_region("id", {"idx"})
        self.assertEqual(result, "id")

    def test_cn_region_unaffected(self):
        from src.core.trading_calendar import compute_effective_region
        result = compute_effective_region("cn", {"cn", "idx"})
        self.assertEqual(result, "cn")

    def test_unknown_region_falls_back_to_cn_open(self):
        from src.core.trading_calendar import compute_effective_region
        result = compute_effective_region("unknown", {"cn", "idx", "us"})
        self.assertEqual(result, "cn")


class TestIDXConfigParsing(unittest.TestCase):
    """Validate config parsing for IDX market review region."""

    def _parse(self, value: str) -> str:
        from src.config import Config
        return Config._parse_market_review_region(value)

    def test_id_accepted(self):
        self.assertEqual(self._parse("id"), "id")

    def test_idx_alias_accepted(self):
        self.assertEqual(self._parse("idx"), "id")

    def test_ID_uppercase_accepted(self):
        self.assertEqual(self._parse("ID"), "id")

    def test_IDX_uppercase_accepted(self):
        self.assertEqual(self._parse("IDX"), "id")

    def test_cn_unchanged(self):
        self.assertEqual(self._parse("cn"), "cn")

    def test_us_unchanged(self):
        self.assertEqual(self._parse("us"), "us")

    def test_both_unchanged(self):
        self.assertEqual(self._parse("both"), "both")

    def test_invalid_falls_back_to_cn(self):
        self.assertEqual(self._parse("hk"), "cn")


class TestYfinanceIDXIndices(unittest.TestCase):
    """Validate YfinanceFetcher.get_main_indices() handles region='idx'."""

    def setUp(self):
        import sys
        from unittest.mock import MagicMock
        from data_provider.yfinance_fetcher import YfinanceFetcher
        self.fetcher = YfinanceFetcher()
        # Ensure yfinance is mocked so import inside get_main_indices doesn't fail
        self._original_yf = sys.modules.get('yfinance')
        sys.modules['yfinance'] = MagicMock()

    def tearDown(self):
        import sys
        if self._original_yf is not None:
            sys.modules['yfinance'] = self._original_yf

    def _call_get_main_indices(self, region: str):
        from unittest.mock import patch
        with patch.object(self.fetcher, '_get_idx_main_indices', return_value=[]) as mock_method:
            self.fetcher.get_main_indices(region=region)
            return mock_method

    def test_get_main_indices_idx_calls_get_idx_main_indices(self):
        mock_method = self._call_get_main_indices("idx")
        mock_method.assert_called_once()

    def test_get_main_indices_id_calls_get_idx_main_indices(self):
        mock_method = self._call_get_main_indices("id")
        mock_method.assert_called_once()


if __name__ == "__main__":
    unittest.main()
