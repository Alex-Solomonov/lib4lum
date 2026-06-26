# lib4lum

A small, config-driven pipeline for building and solving metasurface FDTD models
in Lumerical.

### File Tree

```
project directory/
├── project/
│   │   ├── test.py          # single-lens example
│   │   └── all-in-one.py    # lens / deflector / random ensemble example
│   └── lib4lum/
│       └── ...library files
└── models/
    ├── clean/    # built .ini + unsolved .fsp
    ├── solved/   # solved .fsp (full field, re-openable in Lumerical)
    └── results/  # extracted .npz (complex E + |E|^2 + axes, per monitor)
```

### Pipeline

```python
write_config(cfg, wavelength=..., size=..., type='lens', focal_length=...)
generate_model(cfg, phases=(r, phase))      # build the .fsp
solve_model(fsp, solved_path=...)           # solve -> fields
```

or the batch forms `generate_model_set([cfgs], phases=...)` and
`solve_model_set(clean_dir)`.

- **`write_config`** — writes one `.ini` per model from flat keywords (geometry,
  `type`, profile params). Omit `radii` and `seed`; the library fills them.
- **`generate_model`** — reads the `.ini`, creates a seed if none is set, resolves the
  `n` radii from `seed -> first phase -> the (r, phase) lookup`, and stamps the seed and
  radii back into the `.ini`. With no `phases`, it uses the `[RADII]` already there.
- **`solve_model`** — solves the `.fsp` and returns each monitor's complex `Ex/Ey/Ez`,
  `|E|^2`, and axes.

### Artifacts & reproducibility

- **`clean/<name>.fsp`** built/unsolved · **`solved/<name>.fsp`** full solved
  simulation, re-openable · **`results/<name>.npz`** the extracted fields.
- The **`.ini` is the record**: a model rebuilds from its config alone — seed in
  `[PROFILE] seed`, radii in `[RADII]`. No separate seed files.
- **`.npz` vs solved `.fsp`:** the `.npz` is a light numerical record of the monitor
  fields; the solved `.fsp` is the heavy full simulation you can reopen to re-extract
  anything (H, Poynting, far-field, monitors you didn't add) without re-solving. Set
  `save_solved=False` to keep only the `.npz` — the `clean/.fsp` + `.ini` always rebuild it.
