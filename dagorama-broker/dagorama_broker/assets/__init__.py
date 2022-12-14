from importlib.resources import files
from pathlib import Path


def get_asset_path(asset_name: str) -> Path:
    return Path(str(files(__name__) / asset_name))
