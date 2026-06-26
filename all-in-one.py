from pathlib import Path

import numpy as np

from lib4lum import deploy, model_generator, model_solver

HERE = Path(__file__).resolve().parent
CLEAN = HERE / 'models' / 'clean'
PHASES = HERE.parent.parent / 'T_phi_38nm_830-880nm.txt'   # point at your r-vs-phase lookup

WL = 850e-9
PERIOD = 425e-9
H_DISK = 150e-9
H_SPACER = 38e-9
SIZE = 10                # 21x21 array (aperture 8.93 um)
N = 5

# parse the lookup -> (r, phase); this part is specific to your COMSOL file format
lut = np.genfromtxt(PHASES, comments='%', usecols=(0, 2, 4))
lut = lut[np.isclose(lut[:, 1], 850)]                  # nm slice
lut = lut[np.argsort(lut[:, 0])]
r, phase = lut[:, 0], np.unwrap(lut[:, 2])             # the library handles direction

METAS = [
    ('lens_F3.5wl',     dict(type='lens', focal_length=3.5 * WL)),
    ('lens_F4.5wl',     dict(type='lens', focal_length=4.5 * WL)),
    ('deflector_30deg', dict(type='deflector', theta_x=np.radians(30))),
    ('deflector_40deg', dict(type='deflector', theta_x=np.radians(40))),
    ('random_a',        dict(type='random')),
    ('random_b',        dict(type='random')),
]

cfgs = []
for name, profile in METAS:
    cfg = CLEAN / f'{name}.ini'
    deploy.write_config(cfg, wavelength=WL, size=SIZE, period=PERIOD, n_levels=N,
                        h_disk=H_DISK, h_spacer=H_SPACER, **profile)   # no substrate, z_extent default 10um
    cfgs.append(cfg)

model_generator.generate_model_set(cfgs, phases=(r, phase))
for cfg in cfgs:
    print(cfg.stem, 'seed:', deploy.read_config(cfg)['PROFILE']['seed'])
model_solver.solve_model_set(CLEAN)
