"""Sleeper Kicker-to-Rookie Pick Converter Package."""
import os

from ._version import __version__ as _base_version

__version__ = _base_version + os.getenv("VERSION_SUFFIX", "")

from .kicker_to_pick import run_kicker_scan

__all__ = ["__version__", "run_kicker_scan"]

