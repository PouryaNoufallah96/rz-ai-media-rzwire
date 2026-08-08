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
        self.assertEqual(set(validated), {"mgc", "oasis", "jewelry", "industrial", "real-estate", "trip"})
        self.assertTrue(all(item["enabled"] for item in validated.values()))
        self.assertTrue(all(len(item["backgroundScenes"]) >= 3 for item in validated.values()))

    def test_public_registry_contains_theme_and_market_identity(self):
        brands = public_analytics_brands()
        self.assertEqual([item["id"] for item in brands], ["mgc", "oasis", "jewelry", "industrial", "real-estate", "trip"])
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

    def test_real_estate_has_verified_market_identity_and_visual_references(self):
        from brand_profiles import BRAND_IMAGE_PROFILES

        item = get_analytics_brand("real-estate")
        self.assertEqual(item["name"], "Real Estate Token")
        self.assertEqual(item["symbol"], "REALESTATE")
        self.assertEqual(item["market"]["contract"], "0x32477cf0e324f9a9cb49e8803fa4de9f80f8d0d4")
        self.assertEqual(item["market"]["pool"], "0x742f3a595c83d6a9aa3417c2c7c3f36fb6ee4ac4")
        self.assertEqual(item["market"]["tokenSide"], "base")
        self.assertEqual(item["market"]["coinMarketCapId"], "35949")
        self.assertEqual(item["footer"], "real-estate.game")
        assets = BRAND_IMAGE_PROFILES["Real Estate Token"]["approved_reference_assets"]
        self.assertEqual(len(assets), 10)
        backend_root = Path(__file__).resolve().parent
        for relative_path in assets.values():
            self.assertTrue((backend_root / relative_path).is_file(), relative_path)

    def test_trip_has_verified_market_identity_and_ten_visual_references(self):
        from brand_profiles import BRAND_IMAGE_PROFILES

        item = get_analytics_brand("trip")
        self.assertEqual(item["name"], "Trip Token")
        self.assertEqual(item["symbol"], "TRIP")
        self.assertEqual(item["market"]["network"], "bsc")
        self.assertEqual(item["market"]["contract"], "0xc9bfb93d75645c4681bb63794abf1acad44725e7")
        self.assertEqual(item["market"]["pool"], "0x5837e9c66666d8bcac3e3b0d38cd910225d9e0f2")
        self.assertEqual(item["market"]["tokenSide"], "base")
        self.assertEqual(item["market"]["coinMarketCapId"], "35555")
        assets = BRAND_IMAGE_PROFILES["Trip Token"]["approved_reference_assets"]
        self.assertEqual(len(assets), 10)
        backend_root = Path(__file__).resolve().parent
        for relative_path in assets.values():
            self.assertTrue((backend_root / relative_path).is_file(), relative_path)

    def test_trip_references_use_ten_distinct_editorial_families(self):
        from brand_profiles import BRAND_IMAGE_PROFILES

        expected = {
            "smart_journey_terminal", "destination_discovery", "travel_planning_table",
            "transparent_journey_records", "global_tourism_network", "accommodation_discovery",
            "seamless_mobility_journey", "culture_nature_journey",
            "integrated_travel_ecosystem", "traveler_support_documentary",
        }
        profile = BRAND_IMAGE_PROFILES["Trip Token"]
        reference_families = {key.rsplit(" / ", 1)[-1] for key in profile["approved_reference_assets"]}
        self.assertEqual(reference_families, expected)
        for family_name in expected:
            family = profile["families"][family_name]
            for axis, value in family["default_axes"].items():
                self.assertIn(value, profile["axes"][axis], f"Trip Token: {family_name}/{axis}")

    def test_industrial_and_real_estate_references_use_distinct_editorial_families(self):
        from brand_profiles import BRAND_IMAGE_PROFILES

        expected = {
            "Industrial Token": {
                "factory_campaign", "digital_twin_lab", "traceability_route", "challenge_arena",
                "sustainable_campus", "predictive_machine", "simulation_classroom",
                "verified_service_network", "ranking_forum", "real_economy_landscape",
            },
            "Real Estate Token": {
                "property_progression", "digital_economy_room", "title_verification",
                "architectural_twin", "global_property_network", "access_still_life",
                "verified_transaction", "property_record_stack", "participation_table",
                "sustainable_property_city",
            },
        }
        for brand, expected_families in expected.items():
            profile = BRAND_IMAGE_PROFILES[brand]
            direction_families = {
                key.rsplit("/", 1)[1].strip() for key in profile["approved_directions"]
            }
            self.assertEqual(direction_families, expected_families)
            self.assertEqual(set(profile["approved_directions"]), set(profile["approved_reference_assets"]))
            for family_name in expected_families:
                family = profile["families"][family_name]
                for axis, value in family["default_axes"].items():
                    self.assertIn(value, profile["axes"][axis], f"{brand}: {family_name}/{axis}")

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
