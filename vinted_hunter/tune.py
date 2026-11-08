"""Propuesta manual de pesos mediante regresión logística local."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from vinted_hunter.config import Config, Tuning, load_config, read_yaml
from vinted_hunter.storage.sqlite_store import SQLiteStore


def metrics(expected: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    tp = int(np.sum((expected == 1) & (predicted == 1)))
    fp = int(np.sum((expected == 0) & (predicted == 1)))
    fn = int(np.sum((expected == 1) & (predicted == 0)))
    return {"precision": tp / (tp + fp) if tp + fp else 0,
            "recall": tp / (tp + fn) if tp + fn else 0, "samples": len(expected)}


def fit_logistic(
    features: np.ndarray, labels: np.ndarray, settings: Tuning,
) -> tuple[np.ndarray, float]:
    weights = np.zeros(features.shape[1])
    intercept = 0.0
    for _ in range(settings.iterations):
        probabilities = 1 / (1 + np.exp(-np.clip(features @ weights + intercept, -40, 40)))
        error = probabilities - labels
        weights -= settings.learning_rate * (
            features.T @ error / len(labels) + settings.l2 * weights
        )
        intercept -= settings.learning_rate * float(np.mean(error))
    return weights, intercept


def weighted_scores(
    features: np.ndarray, coefficients: np.ndarray, base: float,
    keys: list[str], parts_cap: float,
) -> np.ndarray:
    contributions = features * coefficients
    if "parts" in keys:
        index = keys.index("parts")
        contributions[:, index] = np.minimum(parts_cap, contributions[:, index])
    return np.clip(base + np.sum(contributions, axis=1), 0, 100)


def profile_scores(
    features: np.ndarray, rows: list[dict[str, Any]], keys: list[str], config: Config,
    global_weights: dict[str, int],
) -> np.ndarray:
    profiles = {p.id: p for p in config.profiles}
    scores = []
    for index, row in enumerate(rows):
        profile = profiles.get(row["profile"])
        weights = {**global_weights, **(profile.scoring_weights if profile else {})}
        coefficients = np.array([weights.get("part" if key == "parts" else key, 0)
                                 for key in keys])
        scores.append(weighted_scores(features[index:index+1], coefficients,
                      weights["base"], keys, weights["max_part_points"])[0])
    return np.array(scores)


def propose(root: Path) -> dict[str, Any]:
    config = load_config(root)
    with SQLiteStore(root / "data/vh.sqlite") as store:
        labels = {r["listing_id"]: r["label"] for r in store.db.execute(
            "SELECT * FROM labels WHERE label IN ('fake','good') ORDER BY captured"
        )}
        records = {r["id"]: r for r in store.records()}
    usable = [(records[key], label) for key, label in labels.items()
              if key in records and records[key]["trace"].get("signals")]
    counts = {label: sum(value == label for _, value in usable) for label in ("good", "fake")}
    if len(usable) < config.scoring.tuning.min_labels or min(counts.values()) < 2:
        return {
            "ready": False, "usable": len(usable), "required": config.scoring.tuning.min_labels,
            "classes": counts, "reason": "Faltan etiquetas fake/good con señales de ambas clases",
        }
    keys = sorted({key for row, _ in usable for key in row["trace"]["signals"]})
    keys = [key for key in keys if key not in {"trusted_seller", "base"}]
    features = np.array([[row["trace"]["signals"].get(key, 0) for key in keys]
                         for row, _ in usable], dtype=float)
    targets = np.array([int(label == "good") for _, label in usable])
    validation = []
    for label in (0, 1):
        indexes = np.flatnonzero(targets == label)
        amount = max(1, int(len(indexes) * config.scoring.tuning.validation_fraction))
        validation.extend(indexes[-amount:])
    test = np.array(sorted(validation), dtype=int)
    train = np.array([i for i in range(len(usable)) if i not in validation], dtype=int)
    fitted, intercept = fit_logistic(features[train], targets[train], config.scoring.tuning)
    threshold = config.scoring.thresholds["good"]
    test_rows = [usable[index][0] for index in test]
    old_scores = profile_scores(features[test], test_rows, keys, config, config.scoring.weights)
    # Diez puntos por unidad logit conservan el umbral good como probabilidad 0,5.
    proposed = np.rint(fitted * 10).astype(int)
    base = int(round(threshold + intercept * 10))
    proposed_weights = {**config.scoring.weights, "base": base}
    proposed_weights.update({"part" if key == "parts" else key: int(value)
                             for key, value in zip(keys, proposed, strict=True)})
    new_scores = profile_scores(features[test], test_rows, keys, config, proposed_weights)
    report = {"ready": True, "usable": len(usable), "train": len(train), "validation": len(test),
              "classes": counts, "before": metrics(targets[test], old_scores >= threshold),
              "after": metrics(targets[test], new_scores >= threshold),
              "validation_policy": "temporal estratificada; confianza de feedback excluida"}
    output = read_yaml(root / "config/scoring.yaml")
    output["weights"].update({"part" if key == "parts" else key: int(value)
                              for key, value in zip(keys, proposed, strict=True)})
    output["weights"]["base"] = base
    output["proposal_metadata"] = {"created": datetime.now(UTC).isoformat(), **report}
    destination = root / "config/scoring.proposed.yaml"
    destination.write_text(yaml.safe_dump(output, sort_keys=False, allow_unicode=True),
                           encoding="utf-8")
    return {**report, "proposal": str(destination)}
