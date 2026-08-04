import cv2

from autocraftofexile.stash_detector import (
    StashSpriteDetector,
    annotate_detections,
)
from tests import PROJECT_ROOT

STASH_EXAMPLE_QUAD_ITEMS = PROJECT_ROOT / "data" / "stash_example_quad_items.png"


# Fixture-only expected composition. None of these coordinates or dimensions is
# imported by, or otherwise visible to, StashItemDetector.
def expected_example_items() -> tuple[tuple[int, int, int, int], ...]:
    expected: list[tuple[int, int, int, int]] = []

    # Three left columns of 1x1 jewellery; the bottom-right cells are empty.
    for row in range(23):
        for column in range(3):
            expected.append((column, row, 1, 1))

    # Right-side fixture bands in quad-grid units.
    for row, width, height, first_column in (
        (0, 2, 2, 6),
        (2, 2, 2, 8),
        (4, 2, 3, 6),
        (7, 2, 3, 6),
        (10, 2, 2, 6),
        (12, 2, 2, 6),
        (14, 2, 1, 12),
        (15, 2, 1, 12),
        (16, 2, 2, 4),
        (18, 2, 2, 4),
    ):
        for column in range(first_column, 24, width):
            if column + width <= 24:
                expected.append((column, row, width, height))

    for column in range(8, 24):
        expected.append((column, 21, 1, 3))

    return tuple(expected)


def cell_iou(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> float:
    fc, fr, fw, fh = first
    sc, sr, sw, sh = second
    left, top = max(fc, sc), max(fr, sr)
    right, bottom = min(fc + fw, sc + sw), min(fr + fh, sr + sh)
    intersection = max(0, right - left) * max(0, bottom - top)
    if not intersection:
        return 0.0
    return intersection / (fw * fh + sw * sh - intersection)


def test_generic_detector_against_described_example_layout() -> None:
    image = cv2.imread(STASH_EXAMPLE_QUAD_ITEMS)
    assert image is not None
    detections = StashSpriteDetector().detect(image)
    cv2.imwrite(
        PROJECT_ROOT / "data" / "test_stash_example_quad_items_detected.png",
        annotate_detections(image, detections),
    )
