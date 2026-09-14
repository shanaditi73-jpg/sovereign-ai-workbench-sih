"""Shared by every tool file."""

import pathlib

OUTPUT_DIR = pathlib.Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
