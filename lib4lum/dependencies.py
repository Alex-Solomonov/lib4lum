import numpy as np
from numpy import typing as npt
import os
import sys
from pathlib import Path
from tqdm import tqdm
from glob import glob
from scipy import interpolate
from psutil import cpu_count


### local packages
from . import (
    phase_profiles,
    model_generator
)

###Auto-detect Lumerical and return the lumapi module
search_roots = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Lumerical",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Lumerical",
]
for root in search_roots:
    api_paths = sorted(root.glob("v*/api/python"))
    if api_paths:
        sys.path.append(str(api_paths[-1]))
        break
else:
    raise FileNotFoundError("Lumerical not found in Program Files")
import lumapi