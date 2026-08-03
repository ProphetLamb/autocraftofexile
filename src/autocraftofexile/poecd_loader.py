import json
import logging
from os import PathLike
from pathlib import Path

import requests

from autocraftofexile import POECD_URL

from .models.poecd import PoeCd

_logger = logging.getLogger(__name__)


def load_poecd_data(file: PathLike[str] | str) -> PoeCd:
    text = _download_poecd_content(Path(file))
    data = _parse_poecd_data(text)
    return data


def _parse_poecd_data(text: str) -> PoeCd:
    _logger.debug("begin CraftOfExile data parse")
    text = text.removeprefix("poecd=")
    data = json.loads(text)
    result = PoeCd.from_dict(data)
    _logger.debug("done CraftOfExile data parse")
    return result


def _download_poecd_content(file: Path) -> str:
    try:
        with open(file, "r", encoding="utf-8") as f:
            _logger.debug("begin CraftOfExile data file read")
            return f.read()
    except FileNotFoundError:
        _logger.debug("begin CraftOfExile data download")
        response = requests.get(POECD_URL, timeout=60)
        response.raise_for_status()
        _logger.debug("done CraftOfExile data download")
        file.write_bytes(response.content)
        _logger.debug("done CraftOfExile data file write")
        return response.content.decode()
