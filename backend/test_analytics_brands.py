import copy
from pathlib import Path
import unittest

from analytics_brands import (
    ANALYTICS_BRANDS,
    get_analytics_brand,
    public_analytics_brands,
    validate_analytics_brand_registry,
)


class AnalyticsBrandRegistryTests(unittest.TestCase):
    def test_current_enabled_registry_is_complete(self):
        validated = validate_analytics_brand_registry()
        self.assertEqual(set(validated), {"mgc", "oasis", "jewelry", "industrial"})
        self.assertTrue(all(item["enabled"] for item in validated.values()))
        self.assertTrue(all(len(item["backgroundScenes"]) >= 3 for item in validated.values()))

    def test_public_registry_contains_theme_and_market_identity(self):
        brands = public_analytics_brands()
        self.assertEqual([item["id"] for item in brands], ["mgc", "oasis", "jewelry", "industrial"])
        self.assertTrue(all(item["logoUrl"] and item["footerLogoUrl"] and item["theme"] and item["market"] for item in brands))
        self.assertTrue(all("artDirectorProfile" not in item for item in brands))

    def test_industrial_has_a_complete_verified_market_identity(self):
        industrial = get_analytics_brand("industrial")
        self.assertEqual(industrial["name"], "Industrial Token")
        self.assertEqual(industrial["symbol"], "INDUSTRIAL")
        self.assertEqual(industrial["market"]["network"], "bsc")
        self.assertEqual(industrial["market"]["contract"], "0x9e06e1203bdc3747ee3ab5fa9488619bcf2a2666")
        self.assertEqual(industrial["market"]["pool"], "0xd5916c07de3ffbb728a07e118fa89b5452ea9602")
        self.assertEqual(industrial["footer"], "industrial.game")
        self.assertTrue(industrial["logoUrl"].endswith("industrial-coin-logo.png"))
        self.assertTrue(industrial["footerLogoUrl"].endswith("industrial-footer-logo.png"))

    def test_industrial_profile_has_ten_approved_visual_references(self):
        from brand_profiles import BRAND_IMAGE_PROFILES

        profile = BRAND_IMAGE_PROFILES["Industrial Token"]
        assets = profile["approved_reference_assets"]
        self.assertEqual(len(assets), 10)
        backend_root = Path(__file__).resolve().parent
        for relative_path in assets.values():
            self.assertTrue((backend_root / relative_path).is_file(), relative_path)

    def test_duplicate_id_or_symbol_fails_closed(self):
        duplicate_id = [copy.deepcopy(ANALYTICS_BRANDS["mgc"]), copy.deepcopy(ANALYTICS_BRANDS["oasis"])]
        duplicate_id[1]["id"] = "mgc"
        with self.assertRaisesRegex(ValueError, "Duplicate or missing analytics brand id"):
            validate_analytics_brand_registry(duplicate_id)

        duplicate_symbol = [copy.deepcopy(ANALYTICS_BRANDS["mgc"]), copy.deepcopy(ANALYTICS_BRANDS["oasis"])]
        duplicate_symbol[1]["symbol"] = "MGC"
        with self.assertRaisesRegex(ValueError, "Duplicate or missing analytics brand symbol"):
            validate_analytics_brand_registry(duplicate_symbol)

    def test_enabled_incomplete_brand_fails_closed(self):
        incomplete = copy.deepcopy(ANALYTICS_BRANDS["mgc"])
        incomplete["id"] = "future"
        incomplete["symbol"] = "FUT"
        incomplete["theme"].pop("accent")
        with self.assertRaisesRegex(ValueError, "incomplete theme"):
            validate_analytics_brand_registry([incomplete])

    def test_enabled_brand_with_unknown_art_director_fails_closed(self):
        incomplete = copy.deepcopy(ANALYTICS_BRANDS["mgc"])
        incomplete["id"] = "unknown-director"
        incomplete["symbol"] = "UNKNOWNDIRECTOR"
        incomplete["artDirectorProfile"] = "Missing Art Director"
        with self.assertRaisesRegex(ValueError, "unknown Art Director"):
            validate_analytics_brand_registry([incomplete])

    def test_enabled_brand_requires_detailed_background_scenes(self):
        incomplete = copy.deepcopy(ANALYTICS_BRANDS["mgc"])
        incomplete["id"] = "no-scenes"
        incomplete["symbol"] = "NOSCENES"
        incomplete["backgroundScenes"] = ["too short"]
        with self.assertRaisesRegex(ValueError, "three detailed background scenes"):
            validate_analytics_brand_registry([incomplete])

    def test_disabled_incomplete_brand_is_not_public(self):
        disabled = {"id": "later", "symbol": "LATER", "enabled": False}
        validated = validate_analytics_brand_registry([disabled])
        self.assertFalse(validated["later"]["enabled"])

    def test_future_coin_fixture_needs_only_one_registry_entry(self):
        future = copy.deepcopy(ANALYTICS_BRANDS["oasis"])
        future.update({"id": "future", "name": "Future Coin", "symbol": "FUT", "logoUrl": "/brands/future.png"})
        future["market"].update({
            "contract": "0x1111111111111111111111111111111111111111",
            "pool": "0x2222222222222222222222222222222222222222",
            "poolName": "FUT / USDT",
        })
        validated = validate_analytics_brand_registry([future])
        self.assertEqual(validated["future"]["symbol"], "FUT")
        self.assertEqual(validated["future"]["theme"]["accent"], future["theme"]["accent"])

    def test_unknown_brand_cannot_resolve(self):
        with self.assertRaisesRegex(ValueError, "Unknown or disabled"):
            get_analytics_brand("missing")


if __name__ == "__main__":
    unittest.main()
