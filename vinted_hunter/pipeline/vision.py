"""Señales visuales locales, sin modelos entrenados."""

from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import imagehash
import numpy as np
import zxingcpp
from PIL import Image, UnidentifiedImageError

from vinted_hunter.pipeline.models import QR, Evidence


def classify_qr(text: str) -> QR:
    try:
        url = urlsplit(text)
        host = (url.hostname or "").lower().rstrip(".")
    except ValueError:
        return "qr_detected_unreadable"
    if url.scheme not in ("http", "https") or not host:
        return "qr_detected_unreadable"
    if host == "certilogo.com" or host.endswith(".certilogo.com"):
        return "certilogo_ok"
    return "qr_foreign_domain"


def _read_qr(gray: np.ndarray) -> tuple[QR, bool]:
    def scan(image: np.ndarray) -> list[QR]:
        return [
            classify_qr(result.text)
            for result in zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)
        ]

    detected = []
    variants = (
        gray,
        cv2.resize(gray, None, fx=2, fy=2),
        cv2.createCLAHE().apply(gray),
    )
    for variant in variants:
        detected.extend(scan(variant))
        if "qr_foreign_domain" in detected:
            return "qr_foreign_domain", True
    if not detected:
        for grid in (2, 3):
            for row in np.array_split(gray, grid):
                for tile in np.array_split(row, grid, axis=1):
                    detected.extend(scan(np.ascontiguousarray(tile)))
    if detected:
        return min(
            detected,
            key=("qr_foreign_domain", "certilogo_ok", "qr_detected_unreadable", "none").index,
        ), True
    found, _ = cv2.QRCodeDetector().detect(gray)
    return ("qr_detected_unreadable" if found else "none"), False


def read_qr(gray: np.ndarray) -> QR:
    return _read_qr(gray)[0]


def phash(image: Image.Image) -> str:
    return str(imagehash.phash(image))


class ReferenceMatcher:
    def __init__(self, directory: Path, thresholds: dict[str, float]) -> None:
        self.orb = cv2.ORB_create(nfeatures=int(thresholds["orb_features"]))
        self.ratio = thresholds["orb_ratio"]
        self.inliers = thresholds["orb_inliers"]
        self.ransac = thresholds["orb_ransac"]
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.references = []
        for file in sorted(directory.glob("*/*")):
            if file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            with Image.open(file) as image:
                keypoints, descriptors = self.orb.detectAndCompute(
                    np.asarray(image.convert("L")),
                    None,
                )
            if descriptors is not None:
                self.references.append((file.parent.name, keypoints, descriptors))

    def parts(self, gray: np.ndarray) -> set[str]:
        if not self.references:
            return set()
        points, descriptors = self.orb.detectAndCompute(gray, None)
        found = set()
        if descriptors is None or len(descriptors) < 2:
            return found
        for part, ref_points, ref_desc in self.references:
            if part in found:
                continue
            pairs = self.matcher.knnMatch(ref_desc, descriptors, k=2)
            good = [a for a, b in pairs if a.distance < self.ratio * b.distance]
            if len(good) >= max(4, self.inliers):
                left = np.float32([ref_points[m.queryIdx].pt for m in good])
                right = np.float32([points[m.trainIdx].pt for m in good])
                _, mask = cv2.findHomography(left, right, cv2.RANSAC, self.ransac)
                if mask is not None and mask.sum() >= self.inliers:
                    found.add(part)
        return found


def inspect_photos(
    images: list[bytes],
    refs: Path,
    stock: Path,
    thresholds: dict[str, float],
    scan_qr: bool,
) -> Evidence:
    evidence = Evidence()
    matcher = ReferenceMatcher(refs, thresholds)
    stock_hashes = set()
    for file in stock.glob("*"):
        if file.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            with Image.open(file) as image:
                stock_hashes.add(phash(image))
    parts = set()
    order = ("qr_foreign_domain", "certilogo_ok", "qr_detected_unreadable", "none")
    for index, body in enumerate(images):
        try:
            with Image.open(BytesIO(body)) as source:
                image = source.convert("RGB")
        except (UnidentifiedImageError, OSError):
            continue
        value = phash(image)
        if index == 0:
            evidence.primary_hash = value
        evidence.hashes.append(value)
        evidence.stock_photo |= value in stock_hashes
        gray = np.asarray(image.convert("L"))
        if scan_qr:
            qr, decoded = _read_qr(gray)
            evidence.qr = min(evidence.qr, qr, key=order.index)
            evidence.qr_decoded |= decoded
        parts |= matcher.parts(gray)
    evidence.parts_present = sorted(parts)
    return evidence
