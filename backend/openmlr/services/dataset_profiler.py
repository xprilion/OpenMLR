"""Dataset Profiler — statistical profiling, validation, and split manager for ML datasets."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _hash_score(seed: int, index: int, item: Any) -> bytes:
    """Generate a deterministic SHA-256 hash digest for an item."""
    encoded = f"{seed}:{index}:{json.dumps(item, sort_keys=True, default=str)}".encode()
    return hashlib.sha256(encoded).digest()


def _hash_sample(items: list[Any], k: int, seed: int = 42) -> list[Any]:
    """Deterministically sample k items using cryptographic hash sorting (safe & reproducible)."""
    if not items or k <= 0:
        return []
    if k >= len(items):
        return list(items)
    scored = [(_hash_score(seed, idx, item), item) for idx, item in enumerate(items)]
    scored.sort(key=lambda x: x[0])
    return [item for _, item in scored[:k]]


def _hash_shuffle(items: list[Any], seed: int = 42) -> list[Any]:
    """Deterministically shuffle items using cryptographic hash sorting."""
    if not items:
        return []
    scored = [(_hash_score(seed, idx, item), item) for idx, item in enumerate(items)]
    scored.sort(key=lambda x: x[0])
    return [item for _, item in scored]


@dataclass
class ColumnProfile:
    """Statistical summary of a single dataset feature/column."""

    name: str
    dtype: str  # numeric, text, categorical, boolean, unknown
    total_count: int
    null_count: int
    null_percentage: float
    unique_count: int
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetProfile:
    """Comprehensive statistical profile of a dataset."""

    file_path: str
    format: str
    total_rows: int
    total_columns: int
    file_size_bytes: int
    columns: dict[str, ColumnProfile] = field(default_factory=dict)
    health_score: int = 100
    warnings: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DatasetProfiler:
    """High-performance dataset profiler, validator, and split generator."""

    @staticmethod
    def detect_format(file_path: str | Path) -> str:
        ext = Path(file_path).suffix.lower()
        mapping = {
            ".csv": "csv",
            ".tsv": "tsv",
            ".tab": "tsv",
            ".jsonl": "jsonl",
            ".ndjson": "jsonl",
            ".json": "json",
            ".txt": "text",
        }
        return mapping.get(ext, "csv")

    @classmethod
    def _load_csv(cls, path: Path, delimiter: str, limit: int | None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                records.append(dict(row))
                if limit and len(records) >= limit:
                    break
        return records

    @classmethod
    def _load_jsonl(cls, path: Path, limit: int | None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    obj = json.loads(line_str)
                    if isinstance(obj, dict):
                        records.append(obj)
                except Exception:
                    continue
                if limit and len(records) >= limit:
                    break
        return records

    @classmethod
    def _load_json(cls, path: Path, limit: int | None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8", errors="replace") as f:
            try:
                data = json.load(f)
                items = (
                    data
                    if isinstance(data, list)
                    else next(
                        (
                            data[k]
                            for k in ("data", "rows", "items", "records", "samples")
                            if isinstance(data.get(k), list)
                        ),
                        [data],
                    )
                )
                for item in items[:limit] if limit else items:
                    if isinstance(item, dict):
                        records.append(item)
            except Exception as e:
                log.warning("JSON parse error: %s", e)
        return records

    @classmethod
    def _load_text(cls, path: Path, limit: int | None) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f):
                if line.strip():
                    records.append({"line_number": idx + 1, "text": line.strip()})
                if limit and len(records) >= limit:
                    break
        return records

    @classmethod
    def load_records(
        cls, file_path: str | Path, limit: int | None = None
    ) -> tuple[list[dict[str, Any]], str, int]:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        fmt = cls.detect_format(path)
        file_size = path.stat().st_size

        if fmt == "csv":
            records = cls._load_csv(path, delimiter=",", limit=limit)
        elif fmt == "tsv":
            records = cls._load_csv(path, delimiter="\t", limit=limit)
        elif fmt == "jsonl":
            records = cls._load_jsonl(path, limit=limit)
        elif fmt == "json":
            records = cls._load_json(path, limit=limit)
        elif fmt == "text":
            records = cls._load_text(path, limit=limit)
        else:
            records = cls._load_csv(path, delimiter=",", limit=limit)

        return records, fmt, file_size

    @classmethod
    def profile(cls, file_path: str | Path, sample_size: int = 5000) -> DatasetProfile:
        records, fmt, file_size = cls.load_records(file_path, limit=sample_size)
        total_rows = len(records)
        if not records:
            return DatasetProfile(
                file_path=str(file_path),
                format=fmt,
                total_rows=0,
                total_columns=0,
                file_size_bytes=file_size,
                health_score=0,
                warnings=["Dataset is empty or unparseable."],
                summary="Empty dataset.",
            )

        all_columns = sorted({k for r in records for k in r.keys()})
        columns_prof: dict[str, ColumnProfile] = {}
        warnings: list[str] = []
        penalty = 0

        for col in all_columns:
            vals = [r.get(col) for r in records]
            non_nulls = [v for v in vals if v is not None and str(v).strip() != ""]
            null_cnt = len(vals) - len(non_nulls)
            null_pct = round((null_cnt / len(vals)) * 100, 2) if vals else 0.0

            if null_pct > 20.0:
                warnings.append(f"Column '{col}' has {null_pct}% missing values.")
                penalty += min(15, int(null_pct // 2))

            dtype, stats = cls._analyze_col(non_nulls, len(vals))
            uniq_cnt = stats.get("unique_count", len({str(v) for v in non_nulls}))

            if dtype == "categorical" and stats.get("imbalance_ratio", 1) > 10.0 and uniq_cnt > 1:
                warnings.append(f"Column '{col}' has class imbalance ({stats['imbalance_ratio']}x).")
                penalty += 10

            columns_prof[col] = ColumnProfile(
                col, dtype, len(vals), null_cnt, null_pct, uniq_cnt, stats
            )

        sample_hashes = [hash(json.dumps(r, sort_keys=True, default=str)) for r in records]
        dup_cnt = total_rows - len(set(sample_hashes))
        if dup_cnt > 0:
            dup_pct = round((dup_cnt / total_rows) * 100, 2)
            warnings.append(f"Found {dup_cnt} ({dup_pct}%) duplicate rows in sample.")
            penalty += min(20, int(dup_pct))

        health = max(0, 100 - penalty)
        summary = f"'{Path(file_path).name}': {total_rows} rows, {len(all_columns)} cols. Health: {health}/100."
        return DatasetProfile(
            str(file_path),
            fmt,
            total_rows,
            len(all_columns),
            file_size,
            columns_prof,
            health,
            warnings,
            summary,
        )

    @classmethod
    def _analyze_col(cls, values: list[Any], total_cnt: int) -> tuple[str, dict[str, Any]]:
        if not values:
            return "unknown", {"unique_count": 0}

        # Boolean
        if all(str(v).lower() in {"true", "false", "0", "1", "yes", "no", "t", "f"} for v in values):
            return "boolean", {
                "unique_count": len({str(v).lower() for v in values}),
                "true_count": sum(1 for v in values if str(v).lower() in ("true", "1", "yes", "t")),
            }

        # Numeric
        try:
            nums = sorted(float(v) for v in values)
            n = len(nums)
            mean = sum(nums) / n
            var = sum((x - mean) ** 2 for x in nums) / max(1, n - 1)
            q25, med, q75 = nums[int(0.25 * n)], nums[int(0.5 * n)], nums[int(0.75 * n)]
            iqr = q75 - q25
            outliers = sum(1 for x in nums if x < (q25 - 1.5 * iqr) or x > (q75 + 1.5 * iqr))
            return "numeric", {
                "min": round(nums[0], 4),
                "max": round(nums[-1], 4),
                "mean": round(mean, 4),
                "std": round(math.sqrt(var), 4),
                "median": round(med, 4),
                "q25": round(q25, 4),
                "q75": round(q75, 4),
                "outlier_count": outliers,
                "unique_count": len(set(nums)),
            }
        except (ValueError, TypeError):
            pass

        # String / Text / Categorical
        strs = [str(v) for v in values]
        uniq_cnt = len(set(strs))
        avg_len = sum(len(s) for s in strs) / len(strs)

        if uniq_cnt <= min(50, max(5, total_cnt // 10)) and avg_len < 64:
            freqs = sorted(
                ((k, sum(1 for x in strs if x == k)) for k in set(strs)),
                key=lambda x: x[1],
                reverse=True,
            )
            imbalance = round(freqs[0][1] / max(1, freqs[-1][1]), 2)
            return "categorical", {
                "unique_count": uniq_cnt,
                "top_classes": dict(freqs[:10]),
                "imbalance_ratio": imbalance,
                "class_distribution": {
                    k: round((v / len(strs)) * 100, 2) for k, v in freqs[:10]
                },
            }

        word_cnts = [len(s.split()) for s in strs]
        toks = sorted(int(w * 1.3) + 1 for w in word_cnts)
        n_tok = len(toks)
        over512 = sum(1 for t in toks if t > 512)

        return "text", {
            "unique_count": uniq_cnt,
            "char_len_avg": round(avg_len, 2),
            "token_est_mean": round(sum(toks) / n_tok, 1),
            "token_est_p95": toks[min(n_tok - 1, int(0.95 * n_tok))],
            "token_est_max": toks[-1],
            "overflow_512_count": over512,
            "overflow_512_pct": round((over512 / n_tok) * 100, 2),
        }

    @classmethod
    def sample_records(
        cls,
        file_path: str | Path,
        n: int = 5,
        offset: int = 0,
        strategy: str = "head",
        label_column: str | None = None,
        seed: int = 42,
    ) -> list[dict[str, Any]]:
        records, _, _ = cls.load_records(file_path)
        if not records:
            return []
        if strategy == "random":
            return _hash_sample(records, k=n, seed=seed)
        if strategy == "stratified" and label_column:
            classes: dict[str, list[dict[str, Any]]] = {}
            for r in records:
                classes.setdefault(str(r.get(label_column, "missing")), []).append(r)
            sampled: list[dict[str, Any]] = []
            per_class = max(1, n // max(1, len(classes)))
            for cl_name in sorted(classes.keys()):
                cl_records = classes[cl_name]
                sampled.extend(_hash_sample(cl_records, k=per_class, seed=seed))
            return sampled[:n]
        return records[offset : offset + n]

    @classmethod
    def validate_dataset(
        cls,
        file_path: str | Path,
        expected_columns: list[str] | None = None,
        max_null_pct: float = 20.0,
        max_token_length: int | None = None,
    ) -> dict[str, Any]:
        profile = cls.profile(file_path, sample_size=3000)
        errors: list[str] = []
        if profile.total_rows == 0:
            return {"valid": False, "errors": ["Dataset is empty."], "health_score": 0}

        if expected_columns:
            missing = [c for c in expected_columns if c not in profile.columns]
            if missing:
                errors.append(f"Missing required columns: {', '.join(missing)}")

        for col, prof in profile.columns.items():
            if prof.null_percentage > max_null_pct:
                errors.append(f"Column '{col}' null percentage {prof.null_percentage}% > {max_null_pct}%")
            if max_token_length and prof.dtype == "text" and prof.stats.get("token_est_max", 0) > max_token_length:
                errors.append(f"Column '{col}' max tokens exceed {max_token_length}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": profile.warnings,
            "health_score": profile.health_score,
            "total_rows": profile.total_rows,
            "total_columns": profile.total_columns,
        }

    @classmethod
    def split_dataset(
        cls,
        file_path: str | Path,
        output_dir: str | Path,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        stratify_column: str | None = None,
        seed: int = 42,
    ) -> dict[str, Any]:
        path = Path(file_path).resolve()
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        records, fmt, _ = cls.load_records(path)
        if not records:
            raise ValueError(f"Cannot split empty dataset: {file_path}")

        tot = train_ratio + val_ratio + test_ratio
        tr_r, val_r = train_ratio / tot, val_ratio / tot
        train_set, val_set, test_set = [], [], []

        if stratify_column:
            classes: dict[str, list[dict[str, Any]]] = {}
            for r in records:
                classes.setdefault(str(r.get(stratify_column, "missing")), []).append(r)
            for cl_records in classes.values():
                shuffled = _hash_shuffle(cl_records, seed=seed)
                n = len(shuffled)
                n_tr, n_v = int(n * tr_r), int(n * val_r)
                train_set.extend(shuffled[:n_tr])
                val_set.extend(shuffled[n_tr : n_tr + n_v])
                test_set.extend(shuffled[n_tr + n_v :])
        else:
            shuffled = _hash_shuffle(records, seed=seed)
            n = len(shuffled)
            n_tr, n_v = int(n * tr_r), int(n * val_r)
            train_set = shuffled[:n_tr]
            val_set = shuffled[n_tr : n_tr + n_v]
            test_set = shuffled[n_tr + n_v :]

        ext = ".csv" if fmt == "csv" else ".jsonl"
        tr_p, val_p, test_p = out_dir / f"train{ext}", out_dir / f"val{ext}", out_dir / f"test{ext}"
        cls._write_records(train_set, tr_p, fmt)
        cls._write_records(val_set, val_p, fmt)
        cls._write_records(test_set, test_p, fmt)

        manifest = {
            "source_file": str(path),
            "stratified_by": stratify_column,
            "seed": seed,
            "total_records": len(records),
            "train_count": len(train_set),
            "val_count": len(val_set),
            "test_count": len(test_set),
            "splits": {"train": str(tr_p), "val": str(val_p), "test": str(test_p)},
        }
        with open(out_dir / "split_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        return manifest

    @staticmethod
    def _write_records(records: list[dict[str, Any]], out_path: Path, fmt: str) -> None:
        if not records:
            out_path.touch()
            return
        if fmt == "csv":
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
                writer.writeheader()
                writer.writerows(records)
        else:
            with open(out_path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, default=str) + "\n")
