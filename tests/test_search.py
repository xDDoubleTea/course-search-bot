"""search.py is pure: no network, no adapter, no Discord."""

import pytest

from search import build_index, fold, search


class TestFold:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("ＡＢＣ", "abc"),
            ("ａｂｃ", "abc"),
            ("０１２", "012"),
            ("微積分Ａ一", "微積分a一"),
            ("Calculus", "calculus"),
            ("", ""),
        ],
        ids=["upper", "lower", "digits", "mixed CJK", "already halfwidth", "empty"],
    )
    def test_folds_fullwidth_alphanumerics(self, raw, expected):
        assert fold(raw) == expected

    @pytest.mark.parametrize("punctuation", ["：", "（", "）", "／", "，"])
    def test_leaves_punctuation_alone(self, punctuation):
        """Matches NTHUMods' [０-９Ａ-Ｚａ-ｚ] scope — folding punctuation changes no match."""
        assert fold(punctuation) == punctuation


class TestSearch:
    @pytest.mark.parametrize(
        "query",
        ["微積分Ａ一", "微積分A一", "ＣＡＬＣＵＬＵＳ", "calculus", "Calculus"],
        ids=[
            "fullwidth both",
            "halfwidth query",
            "fullwidth query",
            "lower",
            "mixed case",
        ],
    )
    def test_fullwidth_folds_on_both_sides(self, catalog, query):
        """The feed itself carries fullwidth Ａ, so folding only the query would miss."""
        assert search(catalog, query)[0].id == "11510MATH101002"

    @pytest.mark.parametrize(
        "typo,expected_id",
        [
            ("calcalus", "11510MATH101002"),
            ("thermodinamics", "11510ESS 240001"),
            ("medcal informatics", "11510CS  555100"),
        ],
    )
    def test_tolerates_a_typo(self, catalog, typo, expected_id):
        assert expected_id in [c.id for c in search(catalog, typo)]

    @pytest.mark.parametrize("query", ["唐傳義", "葉肩宇"])
    def test_finds_by_teacher(self, catalog, query):
        assert search(catalog, query)[0].id == "11510CS  555100"

    def test_finds_by_department(self, catalog):
        assert search(catalog, "MATH")[0].department == "MATH"

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_blank_query_returns_nothing(self, catalog, blank):
        assert search(catalog, blank) == []

    def test_respects_limit(self, catalog):
        assert len(search(catalog, "學", limit=1)) <= 1

    def test_nonsense_returns_nothing(self, catalog):
        assert search(catalog, "zzzzqqqqxxxx") == []

    def test_prebuilt_index_matches_inline(self, catalog):
        """bot.py builds the index once at load; results must not diverge."""
        assert search(catalog, "微積分", index=build_index(catalog)) == search(
            catalog, "微積分"
        )

    def test_index_length_tracks_catalog(self, catalog):
        assert len(build_index(catalog)) == len(catalog)

    def test_exact_title_outranks_longer_matches(self, catalog):
        """partial_ratio scores every superstring 100, so an exact title has to
        be lifted explicitly or it drowns among the courses that contain it."""
        import dataclasses

        exact = dataclasses.replace(catalog[0], id="exact", name_zh="心理學")
        noise = [
            dataclasses.replace(catalog[0], id=f"n{i}", name_zh=f"{p}心理學")
            for i, p in enumerate(["雙語", "健康", "教育", "社會", "認知", "發展"])
        ]
        assert search([*noise, exact], "心理學")[0].id == "exact"

    def test_common_query_does_not_truncate_before_ranking(self, catalog):
        """A query matching far more courses than the limit must still rank
        across all of them, not across an arbitrary prefix."""
        import dataclasses

        many = [
            dataclasses.replace(catalog[0], id=f"m{i}", name_zh=f"專題討論{i:03d}")
            for i in range(200)
        ]
        exact = dataclasses.replace(catalog[0], id="exact", name_zh="專題討論")
        assert search([*many, exact], "專題討論", limit=1)[0].id == "exact"
