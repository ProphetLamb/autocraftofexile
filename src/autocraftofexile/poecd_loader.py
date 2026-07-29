import json
import logging
from os import PathLike
from pathlib import Path

import requests

from autocraftofexile import POECD_FILE, POECD_URL

from .models.poecd import PoeCd


def load_poecd_data(file: PathLike[str] | str | None = None) -> PoeCd:
    text = _download_poecd_content(Path(file) if file else POECD_FILE)
    data = _parse_poecd_data(text)
    return data


def _parse_poecd_data(text: str) -> PoeCd:
    logging.debug("begin CraftOfExile data parse")
    text = text.removeprefix('poecd=')
    data = json.loads(text)
    result = PoeCd.from_dict(data)
    logging.debug("done CraftOfExile data parse")
    return result


def _download_poecd_content(file: Path) -> str:
    try:
        with open(file, "r", encoding="utf-8") as f:
            logging.debug("begin CraftOfExile data file read")
            return f.read()
    except FileNotFoundError:
        logging.debug("begin CraftOfExile data download")
        response = requests.get(POECD_URL, timeout=60)
        response.raise_for_status()
        logging.debug("done CraftOfExile data download")
        file.write_bytes(response.content)
        logging.debug("done CraftOfExile data file write")
        return response.content.decode()
