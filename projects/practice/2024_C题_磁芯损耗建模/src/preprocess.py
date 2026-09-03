"""2024 C 题磁芯损耗数据的无损接入与质量审计管线。

本模块只读取 competition/ 下的官方附件，只向当前练习项目写入派生产物。
它不会删除样本、插补、平滑、缩放、编码类别或划分训练/验证集。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import numbers
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "preprocess.json"
CANONICAL_ROLES = ("training", "waveform_test", "loss_test")
SCALAR_FIELDS = (
    "sample_number",
    "material",
    "temperature",
    "frequency",
    "core_loss",
    "waveform_label",
)


class PreprocessError(RuntimeError):
    """可预期、面向使用者的数据接入错误。"""


_RUNTIME_CACHE: tuple[Any, Any] | None = None


def runtime_dependencies(require_output: bool = False, require_figures: bool = False):
    """延迟导入数据依赖，让缺少附件时仍能先返回准确的输入错误。"""
    global _RUNTIME_CACHE
    if _RUNTIME_CACHE is None:
        try:
            import numpy as np
            import pandas as pd
        except ModuleNotFoundError as exc:  # pragma: no cover - 取决于运行环境
            raise PreprocessError(
                "缺少 numpy/pandas。请先按仓库 environment.yml 创建 math_modeling 环境。"
            ) from exc
        _RUNTIME_CACHE = (np, pd)
    np, pd = _RUNTIME_CACHE

    if require_output:
        try:
            import pyarrow  # noqa: F401
        except ModuleNotFoundError as exc:  # pragma: no cover - 取决于运行环境
            raise PreprocessError(
                "缺少 pyarrow，无法写入 Parquet；请更新 math_modeling 环境。"
            ) from exc

    if require_figures:
        try:
            import matplotlib  # noqa: F401
        except ModuleNotFoundError as exc:  # pragma: no cover - 取决于运行环境
            raise PreprocessError(
                "缺少 matplotlib，无法生成审计图；请更新 math_modeling 环境。"
            ) from exc
    return np, pd


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreprocessError(f"配置文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise PreprocessError(f"配置文件不是有效 JSON：{path}: {exc}") from exc

    if config.get("schema_version") != 1:
        raise PreprocessError("preprocess.json 的 schema_version 必须为 1。")
    roles = config.get("roles")
    required_roles = set(CANONICAL_ROLES) | {"submission_template"}
    if not isinstance(roles, dict) or set(roles) != required_roles:
        raise PreprocessError(f"roles 必须且只能包含：{sorted(required_roles)}")
    for role, spec in roles.items():
        if not isinstance(spec.get("tokens"), list) or not spec["tokens"]:
            raise PreprocessError(f"角色 {role} 必须配置至少一个文件名 token。")
    expected = config.get("expected_waveform_points")
    if expected is not None and (not isinstance(expected, int) or expected <= 0):
        raise PreprocessError("expected_waveform_points 必须为 null 或正整数。")
    return config


def resolve_competition_root(config: Mapping[str, Any]) -> Path:
    configured = (PROJECT_ROOT / str(config["competition_root"])).resolve()
    authoritative = (PROJECT_ROOT.parents[2] / "competition").resolve()
    if configured != authoritative:
        raise PreprocessError(
            "competition_root 必须解析到仓库的 competition/；拒绝读取其他位置。"
        )
    if not configured.is_dir():
        raise PreprocessError(f"competition/ 不存在：{configured}")
    return configured


def discover_attachments(
    competition_root: Path, config: Mapping[str, Any]
) -> dict[str, Path]:
    allowed = {str(ext).casefold() for ext in config["allowed_extensions"]}
    candidates = sorted(
        (
            path.resolve()
            for path in competition_root.rglob("*")
            if path.is_file()
            and path.suffix.casefold() in allowed
            and not path.name.startswith("~$")
        ),
        key=lambda path: path.as_posix().casefold(),
    )
    result: dict[str, Path] = {}
    used: dict[Path, str] = {}
    for role, spec in config["roles"].items():
        tokens = [str(token).casefold() for token in spec["tokens"]]
        matched = [
            path
            for path in candidates
            if any(token in path.name.casefold() for token in tokens)
        ]
        if not matched:
            raise PreprocessError(
                f"未找到 {role} 官方附件；期望文件名包含 {spec['tokens']}，"
                f"请由参赛队员将文件放入 {competition_root}。"
            )
        if len(matched) > 1:
            relative = [path.relative_to(competition_root).as_posix() for path in matched]
            raise PreprocessError(f"{role} 匹配到多个附件，无法安全选择：{relative}")
        selected = matched[0]
        if selected in used:
            raise PreprocessError(
                f"同一文件同时匹配 {used[selected]} 和 {role}：{selected.name}"
            )
        if not is_within(selected, competition_root):
            raise PreprocessError(f"附件越出 competition/：{selected}")
        used[selected] = role
        result[role] = selected
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_header(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    return re.sub(r"[\s_,，。:：;；()（）\[\]{}·/\\\-]+", "", text)


def scalar_field_for_header(value: Any) -> str | None:
    normalized = normalize_header(value)
    if normalized in {"序号", "编号", "样本序号", "样本编号", "id", "sampleid"}:
        return "sample_number"
    if "温度" in normalized or normalized in {"temperature", "tempc", "t"}:
        return "temperature"
    if "频率" in normalized or normalized in {"frequency", "freq", "fhz", "f"}:
        return "frequency"
    if "磁芯损耗" in normalized or normalized in {
        "损耗",
        "coreloss",
        "loss",
        "pw/m3",
    }:
        return "core_loss"
    if "励磁波形" in normalized or normalized in {"波形", "waveform", "wave"}:
        return "waveform_label"
    if "材料" in normalized or normalized in {"material", "materialtype"}:
        return "material"
    return None


def waveform_index_for_header(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value) if value >= 0 else None
    text = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return int(float(text))
    normalized = normalize_header(text)
    if not ("磁通密度" in normalized or normalized.startswith("b")):
        return None
    numeric_tokens = re.findall(r"\d+", normalized)
    return int(numeric_tokens[0]) if len(numeric_tokens) == 1 else None


def inspect_columns(columns: Sequence[Any]) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    scalar_columns: dict[str, Any] = {}
    waveform_pairs: list[tuple[int, int, Any]] = []
    for position, column in enumerate(columns):
        scalar = scalar_field_for_header(column)
        if scalar is not None:
            if scalar in scalar_columns:
                raise PreprocessError(
                    f"字段 {scalar} 匹配到多个列：{scalar_columns[scalar]!r}, {column!r}"
                )
            scalar_columns[scalar] = column
            continue
        waveform_index = waveform_index_for_header(column)
        if waveform_index is not None:
            waveform_pairs.append((waveform_index, position, column))

    if not waveform_pairs:
        raise PreprocessError("未识别到磁通密度序列列；需要数字或 B/磁通密度加序号表头。")
    indices = [pair[0] for pair in waveform_pairs]
    if len(indices) != len(set(indices)):
        duplicates = sorted(index for index, count in Counter(indices).items() if count > 1)
        raise PreprocessError(f"磁通密度序号重复：{duplicates}")
    ordered = sorted(waveform_pairs, key=lambda pair: (pair[0], pair[1]))
    waveform_columns = [pair[2] for pair in ordered]
    metadata = {
        "scalar_headers": {field: str(column) for field, column in scalar_columns.items()},
        "waveform_headers_original_order": [str(pair[2]) for pair in waveform_pairs],
        "waveform_headers_canonical_order": [str(pair[2]) for pair in ordered],
        "waveform_header_indices": [pair[0] for pair in ordered],
        "waveform_columns_reordered": waveform_pairs != ordered,
    }
    return scalar_columns, waveform_columns, metadata


_MATERIAL_TOKEN = re.compile(r"材料\s*([1234一二三四])", re.IGNORECASE)


def infer_material_from_sheet(sheet_name: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(sheet_name)).strip()
    match = _MATERIAL_TOKEN.search(normalized)
    return match.group(0).replace(" ", "") if match else None


def raw_text(value: Any) -> str:
    _, pd = runtime_dependencies()
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    return unicodedata.normalize("NFKC", str(value)).strip()


def value_token(value: Any) -> str:
    """构造不依赖显示格式的稳定哈希 token。"""
    _, pd = runtime_dependencies()
    try:
        if pd.isna(value):
            return "missing"
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return f"bool:{int(value)}"
    if isinstance(value, numbers.Real):
        number = float(value)
        if math.isnan(number):
            return "nan"
        if math.isinf(number):
            return "inf:+" if number > 0 else "inf:-"
        return f"number:{number.hex()}"
    return f"text:{raw_text(value)}"


def hash_tokens(tokens: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for token in tokens:
        encoded = token.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def numeric_series(frame: Any, column: Any | None, row_count: int):
    _, pd = runtime_dependencies()
    if column is None:
        raw = pd.Series([pd.NA] * row_count, dtype="object")
    else:
        raw = frame[column].reset_index(drop=True)
    parsed = pd.to_numeric(raw, errors="coerce").astype("float64")
    raw_missing = raw.map(lambda value: raw_text(value) == "")
    invalid = (~raw_missing) & parsed.isna()
    return raw, parsed, raw_missing, invalid


def required_scalar_fields(role: str) -> set[str]:
    if role == "training":
        return {"material", "temperature", "frequency", "core_loss", "waveform_label"}
    if role == "loss_test":
        return {"material", "temperature", "frequency", "waveform_label"}
    return set()


def canonicalize_sheet(
    frame: Any,
    *,
    role: str,
    source_relative: str,
    file_sha256: str,
    sheet_name: str,
    sheet_index: int,
    source_order_offset: int = 0,
    expected_waveform_points: int | None = None,
) -> tuple[Any, Any, Any, dict[str, Any]]:
    np, pd = runtime_dependencies()
    frame = frame.reset_index(drop=True)
    row_count = len(frame)
    scalar_columns, waveform_columns, column_metadata = inspect_columns(list(frame.columns))
    waveform_count = len(waveform_columns)
    canonical_waveform_names = [f"b_{index:04d}" for index in range(waveform_count)]
    flags: list[set[str]] = [set() for _ in range(row_count)]
    invalid_cells: list[dict[str, Any]] = []

    if expected_waveform_points is not None and waveform_count != expected_waveform_points:
        for item in flags:
            item.add("waveform_point_count_mismatch")

    missing_required = required_scalar_fields(role) - set(scalar_columns)
    inferred_material = None
    if "material" in missing_required:
        inferred_material = infer_material_from_sheet(sheet_name)
        if inferred_material:
            missing_required.remove("material")
    for field in sorted(missing_required):
        for item in flags:
            item.add(f"missing_column_{field}")

    numeric_data: dict[str, Any] = {}
    raw_data: dict[str, Any] = {}
    for field in ("temperature", "frequency", "core_loss"):
        raw, parsed, missing_mask, invalid_mask = numeric_series(
            frame, scalar_columns.get(field), row_count
        )
        raw_data[f"{field}_raw"] = raw.map(raw_text).astype("string")
        numeric_data[field] = parsed
        if scalar_columns.get(field) is not None:
            for row_position in np.flatnonzero(missing_mask.to_numpy()):
                flags[int(row_position)].add(f"missing_{field}")
            for row_position in np.flatnonzero(invalid_mask.to_numpy()):
                flags[int(row_position)].add(f"invalid_{field}")
                invalid_cells.append(
                    {
                        "source_sheet": sheet_name,
                        "source_row": int(row_position) + 2,
                        "field": field,
                        "source_header": str(scalar_columns[field]),
                        "raw_value": raw_text(raw.iloc[int(row_position)]),
                        "reason": "not_numeric",
                    }
                )

    wave_raw = frame[waveform_columns].reset_index(drop=True)
    wave_numeric = wave_raw.apply(pd.to_numeric, errors="coerce").astype("float64")
    wave_numeric.columns = canonical_waveform_names
    elementwise_map = getattr(wave_raw, "map", None)
    if elementwise_map is None:  # pandas < 2.1
        elementwise_map = wave_raw.applymap
    raw_missing_wave = wave_raw.isna() | elementwise_map(
        lambda value: isinstance(value, str) and not value.strip()
    )
    invalid_wave = (~raw_missing_wave) & wave_numeric.isna().set_axis(
        waveform_columns, axis=1
    )
    nonfinite_wave = ~np.isfinite(wave_numeric.to_numpy(dtype="float64"))
    for row_position in range(row_count):
        if bool(raw_missing_wave.iloc[row_position].any()):
            flags[row_position].add("waveform_missing_value")
        if bool(invalid_wave.iloc[row_position].any()):
            flags[row_position].add("waveform_invalid_value")
        if bool(nonfinite_wave[row_position].any()):
            flags[row_position].add("waveform_nonfinite")
    for row_position, column_position in np.argwhere(invalid_wave.to_numpy()):
        source_header = waveform_columns[int(column_position)]
        invalid_cells.append(
            {
                "source_sheet": sheet_name,
                "source_row": int(row_position) + 2,
                "field": canonical_waveform_names[int(column_position)],
                "source_header": str(source_header),
                "raw_value": raw_text(wave_raw.iloc[int(row_position), int(column_position)]),
                "reason": "not_numeric",
            }
        )

    file_tag = file_sha256[:12]
    sample_ids = [
        f"{role}-{file_tag}-S{sheet_index + 1:02d}-R{row_position + 2:06d}"
        for row_position in range(row_count)
    ]
    sample_number_column = scalar_columns.get("sample_number")
    sample_numbers = (
        frame[sample_number_column].map(raw_text).astype("string")
        if sample_number_column is not None
        else pd.Series([""] * row_count, dtype="string")
    )
    material_column = scalar_columns.get("material")
    if material_column is not None:
        material_values = frame[material_column].map(raw_text).astype("string")
        material_source = "column"
    elif inferred_material is not None:
        material_values = pd.Series([inferred_material] * row_count, dtype="string")
        material_source = "sheet_name"
    else:
        material_values = pd.Series([""] * row_count, dtype="string")
        material_source = "missing"
    waveform_column = scalar_columns.get("waveform_label")
    waveform_values = (
        frame[waveform_column].map(raw_text).astype("string")
        if waveform_column is not None
        else pd.Series([""] * row_count, dtype="string")
    )

    for row_position in range(row_count):
        if role in {"training", "loss_test"} and not material_values.iloc[row_position]:
            flags[row_position].add("missing_material")
        if role == "training" and not waveform_values.iloc[row_position]:
            flags[row_position].add("missing_waveform_label")
        frequency = numeric_data["frequency"].iloc[row_position]
        core_loss = numeric_data["core_loss"].iloc[row_position]
        if math.isfinite(frequency) and frequency <= 0:
            flags[row_position].add("nonpositive_frequency")
        if math.isfinite(core_loss) and core_loss < 0:
            flags[row_position].add("negative_core_loss")

    waveform_hashes: list[str] = []
    exact_row_hashes: list[str] = []
    feature_rows: list[dict[str, Any]] = []
    wave_array = wave_numeric.to_numpy(dtype="float64")
    for row_position in range(row_count):
        raw_wave_values = wave_raw.iloc[row_position].tolist()
        waveform_hash = hash_tokens(value_token(value) for value in raw_wave_values)
        waveform_hashes.append(waveform_hash)
        scalar_tokens = [
            value_token(frame[column].iloc[row_position])
            if column is not None
            else "missing-column"
            for column in (scalar_columns.get(field) for field in SCALAR_FIELDS)
        ]
        exact_row_hashes.append(hash_tokens([*scalar_tokens, waveform_hash]))

        values = wave_array[row_position]
        finite_positions = np.flatnonzero(np.isfinite(values))
        finite_values = values[finite_positions]
        feature: dict[str, Any] = {
            "sample_id": sample_ids[row_position],
            "source_attachment": role,
            "waveform_hash": waveform_hash,
            "b_point_count": waveform_count,
            "b_finite_count": int(finite_values.size),
            "b_min": math.nan,
            "b_max": math.nan,
            "b_abs_max": math.nan,
            "b_peak_to_peak": math.nan,
            "b_half_peak_to_peak": math.nan,
            "b_midrange": math.nan,
            "b_mean": math.nan,
            "b_std": math.nan,
            "b_rms": math.nan,
            "b_argmin": pd.NA,
            "b_argmax": pd.NA,
        }
        if finite_values.size:
            minimum = float(np.min(finite_values))
            maximum = float(np.max(finite_values))
            peak_to_peak = maximum - minimum
            feature.update(
                {
                    "b_min": minimum,
                    "b_max": maximum,
                    "b_abs_max": float(np.max(np.abs(finite_values))),
                    "b_peak_to_peak": peak_to_peak,
                    "b_half_peak_to_peak": peak_to_peak / 2.0,
                    "b_midrange": (maximum + minimum) / 2.0,
                    "b_mean": float(np.mean(finite_values)),
                    "b_std": float(np.std(finite_values, ddof=0)),
                    "b_rms": float(np.sqrt(np.mean(np.square(finite_values)))),
                    "b_argmin": int(finite_positions[int(np.argmin(finite_values))]),
                    "b_argmax": int(finite_positions[int(np.argmax(finite_values))]),
                }
            )
            if peak_to_peak == 0.0:
                flags[row_position].add("waveform_constant_finite_values")
        feature_rows.append(feature)

    canonical = pd.DataFrame(
        {
            "sample_id": sample_ids,
            "source_attachment": role,
            "source_file": source_relative,
            "source_sheet": sheet_name,
            "source_row": [index + 2 for index in range(row_count)],
            "source_order": [source_order_offset + index for index in range(row_count)],
            "sample_number_raw": sample_numbers,
            "material_raw": material_values,
            "material_source": material_source,
            "waveform_label_raw": waveform_values,
            **raw_data,
            **numeric_data,
            "waveform_hash": waveform_hashes,
            "exact_row_hash": exact_row_hashes,
            "_quality_flag_set": flags,
        }
    )
    canonical = pd.concat([canonical, wave_numeric], axis=1)
    features = pd.DataFrame(feature_rows)
    invalid_frame = pd.DataFrame(
        invalid_cells,
        columns=(
            "source_sheet",
            "source_row",
            "field",
            "source_header",
            "raw_value",
            "reason",
        ),
    )
    sheet_metadata = {
        "sheet_name": sheet_name,
        "sheet_index": sheet_index,
        "row_count": row_count,
        "column_count": int(len(frame.columns)),
        "waveform_point_count": waveform_count,
        "material_source": material_source,
        "inferred_material": inferred_material,
        **column_metadata,
    }
    return canonical, features, invalid_frame, sheet_metadata


def read_excel_sheets(path: Path) -> tuple[list[tuple[str, Any]], str]:
    _, pd = runtime_dependencies()
    suffix = path.suffix.casefold()
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    try:
        workbook = pd.ExcelFile(path, engine=engine)
        sheets = [
            (sheet_name, pd.read_excel(workbook, sheet_name=sheet_name))
            for sheet_name in workbook.sheet_names
        ]
    except ImportError as exc:
        raise PreprocessError(
            f"读取 {path.name} 需要 {engine}；请按 environment.yml 更新环境。"
        ) from exc
    except Exception as exc:
        raise PreprocessError(f"无法读取官方附件 {path}: {exc}") from exc
    return sheets, engine


def add_duplicate_audit(canonical_by_role: Mapping[str, Any]) -> None:
    _, pd = runtime_dependencies()
    combined = pd.concat(
        [
            frame[[
                "sample_id",
                "source_attachment",
                "waveform_hash",
                "exact_row_hash",
                "waveform_label_raw",
                "temperature",
                "frequency",
                "core_loss",
                "material_raw",
            ]]
            for frame in canonical_by_role.values()
        ],
        ignore_index=True,
    )
    global_wave_count = combined.groupby("waveform_hash")["sample_id"].transform("size")
    attachment_count = combined.groupby("waveform_hash")["source_attachment"].transform(
        "nunique"
    )
    combined["global_wave_count"] = global_wave_count
    combined["attachment_count"] = attachment_count

    lookup = combined.set_index("sample_id")
    for role, frame in canonical_by_role.items():
        within_wave = frame.groupby("waveform_hash")["sample_id"].transform("size")
        within_exact = frame.groupby("exact_row_hash")["sample_id"].transform("size")
        frame["waveform_group_id"] = frame["waveform_hash"].map(
            lambda value: f"wg-{value[:16]}"
        )
        frame["waveform_duplicate_count"] = within_wave.astype("int64")
        frame["exact_row_duplicate_count"] = within_exact.astype("int64")
        frame["cross_attachment_count"] = frame["sample_id"].map(
            lookup["attachment_count"]
        ).astype("int64")
        for position in range(len(frame)):
            flag_set = frame.at[position, "_quality_flag_set"]
            if int(within_wave.iloc[position]) > 1:
                flag_set.add("waveform_duplicate_within_attachment")
            if int(within_exact.iloc[position]) > 1:
                flag_set.add("exact_row_duplicate")
            if int(frame.at[position, "cross_attachment_count"]) > 1:
                flag_set.add("waveform_overlap_across_attachments")

        for _, group in frame.groupby("waveform_hash", sort=False):
            if len(group) <= 1:
                continue
            labels = {value for value in group["waveform_label_raw"] if value}
            if len(labels) > 1:
                for index in group.index:
                    frame.at[index, "_quality_flag_set"].add(
                        "conflicting_waveform_labels"
                    )
            context_columns = ["material_raw", "temperature", "frequency"]
            for _, context in group.groupby(context_columns, dropna=False, sort=False):
                losses = context["core_loss"].dropna().unique()
                if len(losses) > 1:
                    for index in context.index:
                        frame.at[index, "_quality_flag_set"].add(
                            "multiple_core_loss_for_duplicate_context"
                        )


def finalize_flags(canonical_by_role: Mapping[str, Any]) -> None:
    for frame in canonical_by_role.values():
        frame["quality_flags"] = frame["_quality_flag_set"].map(
            lambda flags: ";".join(sorted(flags))
        )


def build_quality_tables(canonical_by_role: Mapping[str, Any]):
    _, pd = runtime_dependencies()
    audit_columns = [
        "sample_id",
        "source_attachment",
        "source_file",
        "source_sheet",
        "source_row",
        "sample_number_raw",
        "material_raw",
        "temperature",
        "frequency",
        "core_loss",
        "waveform_label_raw",
        "waveform_group_id",
        "waveform_duplicate_count",
        "exact_row_duplicate_count",
        "cross_attachment_count",
        "quality_flags",
    ]
    audit = pd.concat(
        [frame[audit_columns] for frame in canonical_by_role.values()],
        ignore_index=True,
    )
    counter: Counter[str] = Counter()
    for value in audit["quality_flags"]:
        if not value:
            counter["no_flags"] += 1
        else:
            counter.update(value.split(";"))
    summary = pd.DataFrame(
        [
            {"quality_flag": flag, "sample_count": count}
            for flag, count in sorted(counter.items())
        ]
    )

    category_rows: list[dict[str, Any]] = []
    dimensions = {
        "source_sheet": "source_sheet",
        "material": "material_raw",
        "temperature": "temperature_raw",
        "waveform_label": "waveform_label_raw",
    }
    for role, frame in canonical_by_role.items():
        for dimension, column in dimensions.items():
            counts = frame[column].fillna("").astype(str).value_counts(dropna=False, sort=False)
            for value, count in sorted(counts.items(), key=lambda item: item[0]):
                category_rows.append(
                    {
                        "source_attachment": role,
                        "dimension": dimension,
                        "value": value if value else "<missing>",
                        "sample_count": int(count),
                    }
                )
    categories = pd.DataFrame(category_rows)
    return audit, summary, categories


def template_mapping_and_alignment(
    template_sheets: Sequence[tuple[str, Any]], canonical_by_role: Mapping[str, Any]
):
    _, pd = runtime_dependencies()
    mapping_rows: list[dict[str, Any]] = []
    alignment_rows: list[dict[str, Any]] = []
    sheet_number_sets: dict[str, set[str]] = {}

    for sheet_name, frame in template_sheets:
        scalar_columns: dict[str, Any] = {}
        for column in frame.columns:
            scalar = scalar_field_for_header(column)
            if scalar and scalar not in scalar_columns:
                scalar_columns[scalar] = column
        number_column = scalar_columns.get("sample_number")
        numbers: set[str] = set()
        for position in range(len(frame)):
            number = raw_text(frame[number_column].iloc[position]) if number_column is not None else ""
            if number:
                numbers.add(number)
            mapping_rows.append(
                {
                    "template_sheet": sheet_name,
                    "source_row": position + 2,
                    "sample_number_raw": number,
                    "raw_row_json": json.dumps(
                        {str(column): raw_text(frame[column].iloc[position]) for column in frame.columns},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            )
        sheet_number_sets[sheet_name] = numbers

    for role in ("waveform_test", "loss_test"):
        source_numbers = {
            value
            for value in canonical_by_role[role]["sample_number_raw"].astype(str)
            if value
        }
        for sheet_name, template_numbers in sheet_number_sets.items():
            intersection = source_numbers & template_numbers
            alignment_rows.append(
                {
                    "source_attachment": role,
                    "template_sheet": sheet_name,
                    "source_number_count": len(source_numbers),
                    "template_number_count": len(template_numbers),
                    "intersection_count": len(intersection),
                    "missing_in_template_count": len(source_numbers - template_numbers),
                    "extra_in_template_count": len(template_numbers - source_numbers),
                    "exact_number_set_match": bool(source_numbers)
                    and source_numbers == template_numbers,
                }
            )
    return pd.DataFrame(mapping_rows), pd.DataFrame(alignment_rows)


def atomic_json(path: Path, value: Any) -> None:
    ensure_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_csv(frame: Any, path: Path) -> None:
    ensure_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig", lineterminator="\n")
    os.replace(temporary, path)


def atomic_parquet(frame: Any, path: Path) -> None:
    ensure_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False, engine="pyarrow", compression="zstd")
    os.replace(temporary, path)


def ensure_output_path(path: Path) -> None:
    if not is_within(path, PROJECT_ROOT):
        raise PreprocessError(f"拒绝写入练习目录之外：{path}")


def save_figures(
    canonical_by_role: Mapping[str, Any],
    features: Any,
    quality_summary: Any,
    figure_root: Path,
    representative_count: int,
    random_seed: int,
) -> list[Path]:
    np, pd = runtime_dependencies(require_figures=True)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_root.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []

    def save(fig: Any, name: str) -> None:
        path = figure_root / name
        ensure_output_path(path)
        temporary = figure_root / f".{name}.tmp.png"
        fig.savefig(
            temporary,
            dpi=160,
            bbox_inches="tight",
            metadata={"Software": "MathModelingPrepare lossless preprocessing"},
        )
        plt.close(fig)
        os.replace(temporary, path)
        outputs.append(path)

    counts = pd.concat(
        [
            frame.assign(_role=role)[["_role", "sample_id"]]
            for role, frame in canonical_by_role.items()
        ],
        ignore_index=True,
    ).groupby("_role").size()
    fig, axis = plt.subplots(figsize=(7, 4))
    counts.plot(kind="bar", ax=axis, color="#4C78A8")
    axis.set(title="Rows by attachment role", xlabel="Attachment role", ylabel="Rows")
    axis.tick_params(axis="x", rotation=20)
    save(fig, "attachment_row_counts.png")

    scalar = pd.concat(
        [frame[["frequency", "core_loss"]] for frame in canonical_by_role.values()],
        ignore_index=True,
    )
    feature_lookup = features.set_index("sample_id")
    scalar["b_abs_max"] = features["b_abs_max"].reset_index(drop=True)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    for axis, column in zip(axes, ("frequency", "core_loss", "b_abs_max")):
        values = scalar[column].replace([np.inf, -np.inf], np.nan).dropna()
        axis.hist(values, bins=40, color="#59A14F", edgecolor="white")
        axis.set_title(column)
        axis.set_ylabel("Rows")
    fig.suptitle("Untransformed scalar distributions")
    save(fig, "scalar_distributions.png")

    candidates: list[tuple[str, Any, int]] = []
    for role, frame in canonical_by_role.items():
        for index, sample_id in enumerate(frame["sample_id"]):
            score = hashlib.sha256(f"{random_seed}:{sample_id}".encode("utf-8")).hexdigest()
            candidates.append((score, frame, index))
    selected = sorted(candidates, key=lambda item: item[0])[:representative_count]
    if selected:
        rows = math.ceil(len(selected) / 3)
        fig, axes = plt.subplots(rows, 3, figsize=(12, 2.7 * rows), squeeze=False)
        for axis, (_, frame, index) in zip(axes.flat, selected):
            wave_columns = [column for column in frame.columns if column.startswith("b_")]
            values = frame.loc[index, wave_columns].to_numpy(dtype="float64")
            axis.plot(np.arange(len(values)), values, linewidth=0.8)
            axis.set_title(str(frame.at[index, "sample_id"]), fontsize=8)
            axis.set_xlabel("Sample index")
            axis.set_ylabel("B (source unit)")
        for axis in axes.flat[len(selected):]:
            axis.axis("off")
        fig.suptitle("Deterministic representative waveforms")
        save(fig, "representative_waveforms.png")

    shown = quality_summary[quality_summary["quality_flag"] != "no_flags"].copy()
    if not shown.empty:
        shown = shown.sort_values("sample_count").tail(20)
        fig, axis = plt.subplots(figsize=(9, max(4, 0.3 * len(shown))))
        axis.barh(shown["quality_flag"], shown["sample_count"], color="#E15759")
        axis.set(title="Quality flags (no rows removed)", xlabel="Rows")
        save(fig, "quality_flags.png")
    return outputs


def run_pipeline(config_path: Path = DEFAULT_CONFIG, skip_figures: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    competition_root = resolve_competition_root(config)
    attachments = discover_attachments(competition_root, config)
    runtime_dependencies(require_output=True, require_figures=not skip_figures)
    _, pd = runtime_dependencies()

    source_manifest: dict[str, Any] = {
        "schema_version": 1,
        "competition_root": competition_root.relative_to(PROJECT_ROOT.parents[2]).as_posix(),
        "expected_waveform_points": config.get("expected_waveform_points"),
        "sources": {},
    }
    canonical_by_role: dict[str, Any] = {}
    feature_frames: list[Any] = []
    invalid_frames: list[Any] = []
    template_sheets: list[tuple[str, Any]] = []

    for role, path in attachments.items():
        file_hash = sha256_file(path)
        sheets, engine = read_excel_sheets(path)
        relative = path.relative_to(competition_root).as_posix()
        source_record: dict[str, Any] = {
            "relative_path": relative,
            "sha256": file_hash,
            "size_bytes": path.stat().st_size,
            "excel_engine": engine,
            "sheets": [],
        }
        if role == "submission_template":
            template_sheets = sheets
            for sheet_index, (sheet_name, frame) in enumerate(sheets):
                source_record["sheets"].append(
                    {
                        "sheet_name": sheet_name,
                        "sheet_index": sheet_index,
                        "row_count": len(frame),
                        "column_count": len(frame.columns),
                        "headers": [str(column) for column in frame.columns],
                    }
                )
        else:
            canonical_parts: list[Any] = []
            order_offset = 0
            for sheet_index, (sheet_name, frame) in enumerate(sheets):
                canonical, features, invalid, sheet_metadata = canonicalize_sheet(
                    frame,
                    role=role,
                    source_relative=relative,
                    file_sha256=file_hash,
                    sheet_name=sheet_name,
                    sheet_index=sheet_index,
                    source_order_offset=order_offset,
                    expected_waveform_points=config.get("expected_waveform_points"),
                )
                order_offset += len(canonical)
                canonical_parts.append(canonical)
                feature_frames.append(features)
                if not invalid.empty:
                    invalid.insert(0, "source_attachment", role)
                    invalid.insert(1, "source_file", relative)
                    invalid_frames.append(invalid)
                source_record["sheets"].append(sheet_metadata)
            canonical_by_role[role] = pd.concat(canonical_parts, ignore_index=True)
        source_manifest["sources"][role] = source_record

    add_duplicate_audit(canonical_by_role)
    finalize_flags(canonical_by_role)
    features = pd.concat(feature_frames, ignore_index=True)
    group_columns = pd.concat(
        [
            frame[[
                "sample_id",
                "waveform_group_id",
                "waveform_duplicate_count",
                "cross_attachment_count",
                "quality_flags",
            ]]
            for frame in canonical_by_role.values()
        ],
        ignore_index=True,
    )
    features = features.merge(group_columns, on="sample_id", how="left", validate="one_to_one")
    audit, summary, categories = build_quality_tables(canonical_by_role)
    invalid_cells = (
        pd.concat(invalid_frames, ignore_index=True)
        if invalid_frames
        else pd.DataFrame(
            columns=[
                "source_attachment",
                "source_file",
                "source_sheet",
                "source_row",
                "field",
                "source_header",
                "raw_value",
                "reason",
            ]
        )
    )
    template_mapping, alignment = template_mapping_and_alignment(
        template_sheets, canonical_by_role
    )

    processed_root = PROJECT_ROOT / "data" / "processed"
    cache_root = PROJECT_ROOT / "data" / "cache"
    table_root = PROJECT_ROOT / "outputs" / "tables"
    metric_root = PROJECT_ROOT / "outputs" / "metrics"
    written: list[Path] = []
    for role in CANONICAL_ROLES:
        output = processed_root / config["roles"][role]["output"]
        frame = canonical_by_role[role].drop(columns=["_quality_flag_set"])
        atomic_parquet(frame, output)
        written.append(output)
    feature_path = processed_root / "base_features.parquet"
    atomic_parquet(features, feature_path)
    written.append(feature_path)

    manifest_path = cache_root / "source_manifest.json"
    atomic_json(manifest_path, source_manifest)
    written.append(manifest_path)
    tables = {
        "data_quality_audit.csv": audit,
        "data_quality_summary.csv": summary,
        "category_counts.csv": categories,
        "invalid_cells.csv": invalid_cells,
        "submission_template_mapping.csv": template_mapping,
        "submission_alignment.csv": alignment,
    }
    for name, frame in tables.items():
        output = table_root / name
        atomic_csv(frame, output)
        written.append(output)

    figure_paths: list[Path] = []
    if not skip_figures:
        figure_paths = save_figures(
            canonical_by_role,
            features,
            summary,
            PROJECT_ROOT / "outputs" / "figures",
            int(config["representative_waveform_count"]),
            int(config["random_seed"]),
        )
        written.extend(figure_paths)

    receipt = {
        "schema_version": 1,
        "source_sha256": {
            role: source_manifest["sources"][role]["sha256"]
            for role in source_manifest["sources"]
        },
        "row_counts": {role: len(frame) for role, frame in canonical_by_role.items()},
        "quality_flag_counts": {
            str(row["quality_flag"]): int(row["sample_count"])
            for row in summary.to_dict(orient="records")
        },
        "deleted_row_count": 0,
        "output_sha256": {
            path.relative_to(PROJECT_ROOT).as_posix(): sha256_file(path)
            for path in sorted(written, key=lambda item: item.as_posix())
        },
    }
    receipt_path = metric_root / "preprocess_receipt.json"
    atomic_json(receipt_path, receipt)
    return receipt


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG, help="预处理 JSON 配置路径"
    )
    parser.add_argument(
        "--skip-figures", action="store_true", help="只生成表格和 Parquet，不生成 PNG"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        receipt = run_pipeline(args.config.resolve(), skip_figures=args.skip_figures)
    except PreprocessError as exc:
        print(f"预处理未执行：{exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
