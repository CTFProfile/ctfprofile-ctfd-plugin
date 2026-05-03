"""
Read and write plugin configuration via CTFd's Configs table.
"""

from CTFd.models import db  # type: ignore


CONFIG_KEYS = [
    "ctfprofile_url",
    "ctfprofile_api_key",
    "ctfprofile_event_slug",
    "ctfprofile_sync_on_solve",
]


def _get(key: str) -> str:
    from CTFd.utils import get_config  # type: ignore
    val = get_config(key)
    return val or ""


def _set(key: str, value: str) -> None:
    from CTFd.utils import set_config  # type: ignore
    set_config(key, value)


def get_all() -> dict:
    return {k: _get(k) for k in CONFIG_KEYS}


def save(data: dict) -> None:
    for key in CONFIG_KEYS:
        if key in data:
            _set(key, data[key])
