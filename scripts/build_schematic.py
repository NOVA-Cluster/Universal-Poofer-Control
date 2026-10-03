#!/usr/bin/env python3
"""Current revision entry point; prior revision is preserved in archive/."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("build_schematic_a3.py")),run_name="__main__")
