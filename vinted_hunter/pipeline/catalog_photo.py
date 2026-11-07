"""Indicios geométricos de una foto de producto o una captura de tienda."""

import cv2
import numpy as np


def catalog_style_photo(rgb: np.ndarray, thresholds: dict[str, float]) -> bool:
    sample = cv2.resize(rgb, (128, 128), interpolation=cv2.INTER_AREA).astype(np.int16)
    edge = np.concatenate((sample[0], sample[-1], sample[1:-1, 0], sample[1:-1, -1]))
    buckets = (edge // 32) @ np.array([64, 8, 1])
    dominant = np.bincount(buckets).argmax()
    background = np.median(edge[buckets == dominant], axis=0)
    delta = thresholds["catalog_background_delta"]
    matches_edge = (np.max(np.abs(edge - background), axis=-1) <= delta).mean()
    if matches_edge >= thresholds["catalog_edge_fraction"]:
        foreground = np.max(np.abs(sample - background), axis=-1) > delta
        interior = cv2.erode((~foreground).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        gray = cv2.cvtColor(sample.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        texture = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
        smooth = bool(interior.any()) and (
            texture[interior].mean() <= thresholds["catalog_background_max_texture"]
        )
        occupied = foreground.mean()
        if smooth and (
            thresholds["catalog_min_foreground"] <= occupied <= thresholds["catalog_max_foreground"]
        ):
            y, x = np.nonzero(foreground)
            limit = thresholds["catalog_center_offset"] * len(sample)
            if abs(x.mean() - 63.5) <= limit and abs(y.mean() - 63.5) <= limit:
                return True

    flat_delta = thresholds["catalog_ui_flat_delta"]
    rows = np.median(sample, axis=1)
    flat = (np.max(np.abs(sample - rows[:, None]), axis=-1) <= flat_delta).mean(axis=1) >= 0.95
    spans = np.flatnonzero(np.diff(np.r_[False, flat, False])).reshape(-1, 2)
    band = thresholds["catalog_ui_band_fraction"] * len(sample)
    contrast = thresholds["catalog_ui_contrast"]
    return any(
        end - start >= band
        and (start <= len(sample) // 4 or end >= 3 * len(sample) // 4)
        and np.max(np.abs(np.diff(rows[start:end], axis=0)), initial=0) >= contrast
        for start, end in spans
    )
