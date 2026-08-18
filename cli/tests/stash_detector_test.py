import cv2

from autocraftofexile.stash_detector import (
    StashSpriteDetector,
    annotate_detections,
)
from tests import PROJECT_ROOT

STASH_EXAMPLE_QUAD_ITEMS = PROJECT_ROOT / "data" / "stash_example_quad_items.png"


def test_generic_detector_against_described_example_layout() -> None:
    image = cv2.imread(STASH_EXAMPLE_QUAD_ITEMS)
    assert image is not None
    det = StashSpriteDetector()
    detections = det.detect(image)
    cv2.imwrite(
        PROJECT_ROOT / "data" / "test_stash_example_quad_items_detected.png",
        annotate_detections(image, detections),
    )
