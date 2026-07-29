from src.autocraftofexile.gui_config import load_gui_config
from tests import GUI_EXAMPLE


def test_gui_config_load() -> None:
    config = load_gui_config(GUI_EXAMPLE)
    assert config != None
