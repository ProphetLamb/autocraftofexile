from autocraftofexile.poecd_loader import load_poecd_data
from tests import POECD_EXAMPLE


def test_load_poecd_data() -> None:
    data = load_poecd_data(POECD_EXAMPLE)
    assert data != None
