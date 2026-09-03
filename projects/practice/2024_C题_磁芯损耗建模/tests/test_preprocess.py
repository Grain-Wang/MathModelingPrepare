from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "src" / "preprocess.py"
SPEC = importlib.util.spec_from_file_location("core_loss_preprocess", MODULE_PATH)
preprocess = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = preprocess
SPEC.loader.exec_module(preprocess)


class HeaderTests(unittest.TestCase):
    def test_scalar_aliases_and_waveform_headers(self) -> None:
        self.assertEqual(preprocess.scalar_field_for_header("温度，℃"), "temperature")
        self.assertEqual(preprocess.scalar_field_for_header("频率，Hz"), "frequency")
        self.assertEqual(preprocess.scalar_field_for_header("磁芯损耗，W/m³"), "core_loss")
        self.assertEqual(preprocess.scalar_field_for_header("励磁波形"), "waveform_label")
        self.assertEqual(preprocess.waveform_index_for_header(0), 0)
        self.assertEqual(preprocess.waveform_index_for_header("B_1023"), 1023)
        self.assertEqual(
            preprocess.waveform_index_for_header("0（磁通密度B，T）"), 0
        )
        self.assertIsNone(preprocess.waveform_index_for_header("备注"))

    def test_duplicate_waveform_indices_fail(self) -> None:
        with self.assertRaises(preprocess.PreprocessError):
            preprocess.inspect_columns(["温度", 0, "B_0"])


class CanonicalizationTests(unittest.TestCase):
    def make_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "温度，℃": [25, 25, 50],
                "频率，Hz": [1000, 1000, 0],
                "磁芯损耗，W/m³": [10.0, 11.0, -1.0],
                "励磁波形": ["正弦波", "三角波", "正弦波"],
                0: [0.0, 0.0, "bad"],
                1: [1.0, 1.0, 2.0],
                2: [0.0, 0.0, 2.0],
            }
        )

    def canonicalize(self):
        frame = self.make_frame()
        original = frame.copy(deep=True)
        result = preprocess.canonicalize_sheet(
            frame,
            role="training",
            source_relative="data/附件一.xlsx",
            file_sha256="a" * 64,
            sheet_name="材料1",
            sheet_index=0,
            expected_waveform_points=3,
        )
        pd.testing.assert_frame_equal(frame, original)
        return result

    def test_lossless_rows_ids_and_base_features(self) -> None:
        canonical, features, invalid, metadata = self.canonicalize()
        self.assertEqual(len(canonical), 3)
        self.assertTrue(canonical["sample_id"].is_unique)
        self.assertEqual(canonical.loc[0, "material_raw"], "材料1")
        self.assertEqual(canonical.loc[0, "b_0001"], 1.0)
        self.assertEqual(features.loc[0, "b_abs_max"], 1.0)
        self.assertEqual(features.loc[0, "b_peak_to_peak"], 1.0)
        self.assertEqual(features.loc[0, "b_argmax"], 1)
        self.assertEqual(metadata["waveform_point_count"], 3)
        self.assertEqual(len(invalid), 1)
        self.assertEqual(invalid.loc[0, "raw_value"], "bad")

    def test_only_flags_invalid_values(self) -> None:
        canonical, _, _, _ = self.canonicalize()
        third = canonical.loc[2, "_quality_flag_set"]
        self.assertIn("nonpositive_frequency", third)
        self.assertIn("negative_core_loss", third)
        self.assertIn("waveform_invalid_value", third)
        self.assertIn("waveform_nonfinite", third)

    def test_hashes_and_ids_are_deterministic(self) -> None:
        first = self.canonicalize()[0]
        second = self.canonicalize()[0]
        self.assertEqual(first["sample_id"].tolist(), second["sample_id"].tolist())
        self.assertEqual(first["waveform_hash"].tolist(), second["waveform_hash"].tolist())
        self.assertEqual(first["exact_row_hash"].tolist(), second["exact_row_hash"].tolist())

    def test_duplicate_and_cross_attachment_flags(self) -> None:
        train, _, _, _ = self.canonicalize()
        test = train.iloc[[0]].copy(deep=True).reset_index(drop=True)
        test["sample_id"] = "waveform_test-bbbbbbbbbbbb-S01-R000002"
        test["source_attachment"] = "waveform_test"
        test["_quality_flag_set"] = [set()]
        by_role = {"training": train, "waveform_test": test}
        preprocess.add_duplicate_audit(by_role)
        preprocess.finalize_flags(by_role)
        self.assertIn("waveform_duplicate_within_attachment", train.loc[0, "quality_flags"])
        self.assertIn("conflicting_waveform_labels", train.loc[0, "quality_flags"])
        self.assertIn("waveform_overlap_across_attachments", test.loc[0, "quality_flags"])


class DiscoveryAndOutputTests(unittest.TestCase):
    def test_discovery_requires_exactly_one_file_per_role(self) -> None:
        config = json.loads((PROJECT_ROOT / "config" / "preprocess.json").read_text("utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(preprocess.PreprocessError, "未找到 training"):
                preprocess.discover_attachments(root, config)

            for token in ("附件一", "附件二", "附件三", "附件四"):
                (root / f"{token}.xlsx").touch()
            found = preprocess.discover_attachments(root, config)
            self.assertEqual(set(found), set(config["roles"]))
            (root / "附件一_副本.xlsx").touch()
            with self.assertRaisesRegex(preprocess.PreprocessError, "匹配到多个附件"):
                preprocess.discover_attachments(root, config)

    def test_parquet_round_trip_without_row_loss(self) -> None:
        if importlib.util.find_spec("pyarrow") is None:
            self.skipTest("pyarrow is not installed in this test environment")
        source = CanonicalizationTests().make_frame()
        canonical, features, _, _ = preprocess.canonicalize_sheet(
            source,
            role="training",
            source_relative="data/附件一.xlsx",
            file_sha256="a" * 64,
            sheet_name="材料1",
            sheet_index=0,
            expected_waveform_points=3,
        )
        preprocess.add_duplicate_audit({"training": canonical})
        preprocess.finalize_flags({"training": canonical})
        canonical = canonical.drop(columns=["_quality_flag_set"])
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "data" / "cache") as temporary:
            canonical_path = Path(temporary) / "canonical.parquet"
            feature_path = Path(temporary) / "features.parquet"
            preprocess.atomic_parquet(canonical, canonical_path)
            preprocess.atomic_parquet(features, feature_path)
            restored_canonical = pd.read_parquet(canonical_path)
            restored_features = pd.read_parquet(feature_path)
            self.assertEqual(len(restored_canonical), len(source))
            self.assertEqual(len(restored_features), len(source))
            self.assertEqual(
                restored_canonical["sample_id"].tolist(), canonical["sample_id"].tolist()
            )


if __name__ == "__main__":
    unittest.main()
