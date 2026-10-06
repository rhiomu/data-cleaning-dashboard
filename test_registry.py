import os
import json
import unittest

# Locate directory containing this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(TEST_DIR, 'datasets_registry.json')
JS_PATH = os.path.join(TEST_DIR, 'datasets_registry.js')


class TestDatasetsRegistry(unittest.TestCase):
    def test_json_file_exists(self):
        """datasets_registry.json must exist."""
        self.assertTrue(os.path.exists(JSON_PATH), f"File not found: {JSON_PATH}")

    def test_js_file_exists(self):
        """datasets_registry.js must exist."""
        self.assertTrue(os.path.exists(JS_PATH), f"File not found: {JS_PATH}")

    def test_registry_structure(self):
        """datasets_registry.json must contain 12 valid datasets with 18 GT rows and 18 rubric items each."""
        self.assertTrue(os.path.exists(JSON_PATH), "Cannot test structure without registry JSON file")
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            registry = json.load(f)

        expected_ids = [f"set{i:02d}" for i in range(1, 13)]
        self.assertEqual(sorted(list(registry.keys())), expected_ids, "Registry must contain keys set01..set12")
        self.assertEqual(len(registry), 12, "Registry must contain exactly 12 datasets")

        required_dataset_keys = ["id", "name", "filenamePattern", "pkCol", "headers", "groundTruthRows", "rubric"]
        required_rubric_keys = ["#", "level", "origRow", "col", "origVal", "correctVal", "askOwner", "explanation"]

        for set_id, dataset in registry.items():
            for key in required_dataset_keys:
                self.assertIn(key, dataset, f"Dataset {set_id} missing required top-level key '{key}'")

            self.assertEqual(dataset["id"], set_id, f"Dataset id mismatch in {set_id}")
            self.assertIsInstance(dataset["name"], str, f"Dataset {set_id} name must be str")
            self.assertTrue(len(dataset["name"]) > 0, f"Dataset {set_id} name is empty")
            self.assertIsInstance(dataset["filenamePattern"], str, f"Dataset {set_id} filenamePattern must be str")
            self.assertIsInstance(dataset["headers"], list, f"Dataset {set_id} headers must be list")
            self.assertTrue(len(dataset["headers"]) >= 5, f"Dataset {set_id} headers too short")

            # Check Ground Truth rows
            gt_rows = dataset["groundTruthRows"]
            self.assertIsInstance(gt_rows, list, f"Dataset {set_id} groundTruthRows must be list")
            self.assertEqual(len(gt_rows), 18, f"Dataset {set_id} must have exactly 18 groundTruthRows, got {len(gt_rows)}")

            for r_idx, row in enumerate(gt_rows):
                self.assertIsInstance(row, dict, f"Row {r_idx} in {set_id} must be a dict")
                for header in dataset["headers"]:
                    self.assertIn(header, row, f"Row {r_idx} in {set_id} missing header '{header}'")

            # Check Rubric checkpoints
            rubric = dataset["rubric"]
            self.assertIsInstance(rubric, list, f"Dataset {set_id} rubric must be list")
            self.assertEqual(len(rubric), 18, f"Dataset {set_id} must have exactly 18 rubric checkpoints, got {len(rubric)}")

            star_count = 0
            for item_idx, item in enumerate(rubric):
                self.assertIsInstance(item, dict, f"Rubric item {item_idx} in {set_id} must be a dict")
                for r_key in required_rubric_keys:
                    self.assertIn(r_key, item, f"Rubric item {item_idx} in {set_id} missing required key '{r_key}'")

                self.assertIsInstance(item["askOwner"], bool, f"Rubric item {item_idx} in {set_id} 'askOwner' must be bool")
                if item["askOwner"]:
                    star_count += 1
                self.assertIn(item["level"], ["ง่าย", "กลาง", "ยาก"], f"Invalid level in {set_id} rubric #{item_idx}")
                self.assertTrue(len(str(item["col"])) > 0, f"Empty col in {set_id} rubric #{item_idx}")
                self.assertTrue(len(str(item["explanation"])) > 0, f"Empty explanation in {set_id} rubric #{item_idx}")

            self.assertEqual(star_count, 5, f"Dataset {set_id} should have exactly 5 star checkpoints, got {star_count}")

    def test_js_export_validity(self):
        """datasets_registry.js must define window.DATASETS_REGISTRY and match JSON."""
        self.assertTrue(os.path.exists(JS_PATH), "Cannot test JS export without registry JS file")
        with open(JS_PATH, 'r', encoding='utf-8') as f:
            js_content = f.read()

        self.assertIn("window.DATASETS_REGISTRY", js_content)
        self.assertIn("set01", js_content)
        self.assertIn("set12", js_content)


if __name__ == '__main__':
    unittest.main()
