from .dependencies import *
from . import phase_profiles, seed_generator
from .deploy import read_config, _set_seed


def _load_nk(path):
    '''
    Read a [wl_um, value] CSV for dispersion
    '''
    d = np.genfromtxt(path, delimiter=',', encoding='utf-8-sig')
    d = d[~np.isnan(d).any(axis=1)] # drops headers
    return d[:, 0], d[:, 1]

def _register_mat(client, n_csv: str, k_csv: str | None = None, name: str | None = None, mat_dir: str | Path | None = None):
    '''
    Register an isotropic (n, k) material from distinct csv files
    '''
    base = Path(mat_dir or '.')
    wl_um, n = _load_nk(base / n_csv.strip())
    k = np.interp(wl_um, *_load_nk(base / k_csv.strip())) if k_csv else np.zeros_like(n)
    name = name if name else Path(n_csv.strip()).stem # drops spaghetti
    data = np.column_stack([299792458.0 / (wl_um * 1e-6), (n + 1j * k) ** 2])
    m = client.addmaterial("Sampled data")
    client.setmaterial(m, "name", name)
    client.setmaterial(name, "max coefficients", 6)
    client.setmaterial(name, "tolerance", 0.01)
    client.setmaterial(name, "sampled data", data[np.argsort(data[:, 0].real)])
    return name

def generate_model(config_path: str | Path | None = None,
                       save_path: str | Path | None = None,
                       materials_dir: str | Path | None = None,
                       seed: int | None = None) -> str:
    '''
    Build a metasurface model described by the ini

    Args:
        config_path: Path to the .ini. None -> models/default_model_config.ini.
        save_path: Where to write the .fsp. None -> <config path>.fsp.
        materials_dir: Directory the [MATERIALS] CSV files resolve against
            (eval-side; not part of the reproducible config). None -> cwd.
        seed: Realization seed. None -> use [PROFILE] seed from the config.

    Returns:
        (str) save_path

    Raises:
        ValueError: If the lens focus would fall outside the FDTD domain.
    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    if config_path is None:
        config_path = MODELS_PATH / 'default_model_config.ini'
        print(f"No config provided, defaulting to {config_path}")
    config_path = Path(config_path)

    p = read_config(config_path)
    profile = p['PROFILE']
    n = p['STRUCTURE']['n_levels']
    wl = p['SOLVER']['wavelength']
    period = p['STRUCTURE']['period']
    size = p['STRUCTURE']['size']
    h_disk = p['UNIT CELL']['h_disk']
    h_spacer = p['UNIT CELL']['h_spacer']
    radii = p['RADII']['radii']
    z_extent = p['BOX']['z_extent']

    z_max = 2 * h_disk + h_spacer + z_extent
    z_focal = profile['focal_length'] if profile['type'] == 'lens' else None
    if z_focal is not None and z_focal >= z_max:
        raise ValueError(f"lens focus z={z_focal} is outside the domain (z_max={z_max}); raise z_extent")

    if save_path is None:
        save_path = config_path.with_suffix('.fsp')
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if seed is None:
        seed = profile['seed']
    if seed is None:
        seed = int(seed_generator.generate_seeds(1)[0])
    if seed != profile['seed']:
        _set_seed(config_path, seed)
        profile['seed'] = seed
    quasi = build_quasi(profile, wl, period, size, n, seed)
    radii_etalon = phase_profiles.get_radii(quasi, radii)
    build_model(radii_etalon, str(save_path), config_path=str(config_path), materials_dir=materials_dir)
    return str(save_path)


def generate_model_set(config_paths: list[str | Path], out_dir: str | Path | None = None,
                       materials_dir: str | Path | None = None) -> list[str]:
    '''
    Build one model per config -- batch over an arbitrary list of designs

    Each config completely specifies each model, seed in [PROFILE] determines a realization

    Args:
        config_paths: The .ini paths, one per model
        out_dir: Directory for .fsp files. Defaults to config directory, if not provided
        materials_dir: [MATERIALS] csv dir.

    Returns:
        fsp paths in input order
    '''
    paths = []
    for config_path in config_paths:
        config_path = Path(config_path)
        save_path = Path(out_dir) / f'{config_path.stem}.fsp' if out_dir is not None else None
        paths.append(generate_model(config_path, save_path, materials_dir))
    return paths


def build_quasi(profile: dict, wl: float, period: float, size: int, n: int, seed: int) -> npt.NDArray[np.int_]:
    '''
    Build the quasi-phase map for the configured profile.

    Args:
        profile: The [PROFILE] config section. Always has 'type'; a lens uses
            'focal_length', a deflector uses 'theta_x'/'theta_y' (default 0.0),
            random/custom use neither.
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        size: Number of cells from the centre to the edge.
        n: Number of quantisation levels.
        seed: Realization seed; used only by the random profile.

    Returns:
        Integer quasi-phase map of shape (2*size+1, 2*size+1), values in [0, n).

    Raises:
        ValueError: For an unknown profile type ('custom' maps are caller-supplied).
    '''
    kind = profile['type']
    if kind == 'lens':
        return phase_profiles.lens_profile(profile['focal_length'], wl, period, size, n)
    if kind == 'deflector':
        return phase_profiles.deflector_profile(
            profile.get('theta_x', 0.0), profile.get('theta_y', 0.0), wl, period, size, n)
    if kind == 'random':
        return phase_profiles.random_profile(n, size, seed)
    raise ValueError(f"profile type {kind!r} not built here (custom maps are caller-supplied)")

def build_model(radii: npt.NDArray[np.float64], save_path: str,
                config_path: str | Path | None = None,
                materials_dir: str | Path | None = None,
                source_wl: float | None = None,
                source_span: float = 0.0,
                polarization: str = 'x',
                mesh_dx: float | None = None,
                position_offsets: npt.NDArray[np.float64] | None = None,
                lateral_bound: float | None = None,
                refine_y0_plane: bool = False,
                refine_y0_dx_wl: float = 0.01) -> str:
    """Build a Lumerical FDTD model from a precomputed radii grid + the ini.

    Wavelength, period, layer heights, materials and box are read from the
    config; the remaining kwargs are Alex Solomonov's optional source/mesh/
    positional knobs, all neutral (no-op) by default.

    Args:
        radii: 2D disk-radii grid (m), shape (2*size+1, 2*size+1).
        save_path: Where to write the .fsp.
        config_path: Path to the .ini. None -> models/default_model_config.ini.
        materials_dir: Directory the [MATERIALS] CSV files resolve against. None -> cwd.
        source_wl: Source centre wavelength (m). None -> the ini's wavelength.
        source_span: Source wavelength span (m). 0 -> single wavelength.
        polarization: Source polarization, 'x' | 'y' | 'xy'.
        mesh_dx: Uniform mesh size (m). None -> Lumerical adaptive mesh.
        position_offsets: Per-pillar (dx, dy) displacements (m), shape (n, n, 2).
            None -> regular lattice (no positional disorder). Per Wan et al. APL 2025.
        lateral_bound: FDTD half-width in x/y (m). None -> (size+2)*period.
        refine_y0_plane: Add a y=0 mesh override for FWHM_x accuracy. False -> off.
        refine_y0_dx_wl: Mesh cell size (in wl units) when refine_y0_plane is True.

    Returns:
        save_path.

    Raises:
        ValueError: On invalid polarization or a position_offsets shape mismatch.
    """
    if polarization not in ('x', 'y', 'xy'):
        raise ValueError(f"polarization must be 'x', 'y', or 'xy'; got {polarization!r}")

    p = read_config(config_path)
    wl = p['SOLVER']['wavelength']
    period = p['STRUCTURE']['period']
    h_disk = p['UNIT CELL']['h_disk']
    h_spacer = p['UNIT CELL']['h_spacer']
    materials = p['MATERIALS']
    substrate_n = float(materials['substrate'])
    mesh_accuracy = int(p['BOX']['mesh_accuracy'])
    monitor_z_min = p['BOX']['z_min']
    monitor_z_max = 2 * h_disk + h_spacer + p['BOX']['z_extent']
    monitor_z_focal = p['PROFILE']['focal_length'] if p['PROFILE']['type'] == 'lens' else None

    n = radii.shape[0]
    size = (n - 1) // 2
    X, Y = phase_profiles.make_grid(size, period)
    if position_offsets is not None:
        if position_offsets.shape != (n, n, 2):
            raise ValueError(f"position_offsets must have shape ({n},{n},2); got {position_offsets.shape}")
        X = X + position_offsets[..., 0]
        Y = Y + position_offsets[..., 1]
    bound = lateral_bound if lateral_bound is not None else (size + 2) * period

    if source_wl is None:
        source_wl = wl

    # FDTD
    try:
        client = lumapi.FDTD(hide = True)
    except Exception as exc:
        raise RuntimeError(
            "Could not start Lumerical FDTD.\n"
            "Kill stale Lumerical processes in Task Manager and retry.\n"
            "If the problem persists, launch Lumerical GUI manually. License Manager Daemon may require a restart."
        ) from exc

    try:
        solver = client.addfdtd(dimension='3D',
                                x_min=-bound, x_max=bound,
                                y_min=-bound, y_max=bound,
                                z_min=monitor_z_min, z_max=monitor_z_max)
        if mesh_dx is not None:
            solver.mesh_type = 'uniform'
            solver.dx = mesh_dx
            solver.dy = mesh_dx
            solver.dz = mesh_dx

        if mesh_accuracy is not None:
            solver.mesh_accuracy = mesh_accuracy

        # Substrate
        if substrate_n is not None:
            client.addrect(x_min=-bound, x_max=bound,
                           y_min=-bound, y_max=bound,
                           z_min=monitor_z_min, z_max=0,
                           name='Substrate', index=substrate_n)

        # Source
        pol_angles = {'x': [0], 'y': [90], 'xy': [0, 90]}
        for angle in pol_angles[polarization]:
            source = client.addplane(x_min=-size*period, x_max=size*period,
                                     y_min=-size*period, y_max=size*period,
                                     z=-2e-06)
            source.injection_axis = 'z-axis'
            source.polarization_angle = angle
            source.center_wavelength = source_wl
            source.wavelength_span = source_span

        # Structure groups - batched via Lumerical script (single IPC call)
        client.putv('X_arr', X.flatten())
        client.putv('Y_arr', Y.flatten())
        client.putv('R_arr', radii.flatten())
        client.putv('h_d', h_disk)
        client.putv('h_s', h_spacer)
        client.putv('N_sq', n*n)

        disk_mat = (materials or {}).get('disk', 'Si (Silicon) - Palik')
        if '.csv' in str(disk_mat).lower():
            parts = [s.strip() for s in str(disk_mat).split(',')]   # n_csv[, k_csv[, name]]
            disk_mat = _register_mat(client, *parts, mat_dir=materials_dir)
        client.putv('disk_mat', disk_mat)
        client.putv('spacer_n', float((materials or {}).get('spacer', 1.5)))

        script = """
addstructuregroup; set("name", "Bottom_disk");
addstructuregroup; set("name", "Spacer");
addstructuregroup; set("name", "Top_disk");

for(i=1:N_sq) {
        addcircle;
        set("x", X_arr(i)); set("y", Y_arr(i));
        set("z min", 0); set("z max", h_d);
        set("radius", R_arr(i));
        set("name", "Bot_disk_" + num2str(i));
        set("material", disk_mat);
        addtogroup("Bottom_disk");

        addcircle;
        set("x", X_arr(i)); set("y", Y_arr(i));
        set("z min", h_d); set("z max", h_d + h_s);
        set("radius", R_arr(i));
        set("name", "Spacer_" + num2str(i));
        set("index", spacer_n);
        addtogroup("Spacer");

        addcircle;
        set("x", X_arr(i)); set("y", Y_arr(i));
        set("z min", h_d + h_s); set("z max", 2*h_d + h_s);
        set("radius", R_arr(i));
        set("name", "Top_disk_" + num2str(i));
        set("material", disk_mat);
        addtogroup("Top_disk");
}
"""
        client.eval(script)

        # Monitors
        monitor = client.addprofile(name='Monitor Y', monitor_type='2D Y-normal')
        monitor.x_min = -bound
        monitor.x_max = bound
        monitor.z_min = monitor_z_min
        monitor.z_max = monitor_z_max

        monitor = client.addprofile(name='Monitor X', monitor_type='2D X-normal')
        monitor.y_min = -bound
        monitor.y_max = bound
        monitor.z_min = monitor_z_min
        monitor.z_max = monitor_z_max

        if monitor_z_focal is not None:
            monitor = client.addprofile(name='Monitor Z', monitor_type='2D Z-normal')
            monitor.x_min = -bound
            monitor.x_max = bound
            monitor.y_min = -bound
            monitor.y_max = bound
            monitor.z = monitor_z_focal

        # Optional y=0 mesh override - refines FWHM_x sampling at high NA.
        # Added after monitors so the auto-mesh recomputes only once.
        if refine_y0_plane:
            dx = refine_y0_dx_wl * wl
            client.addmesh(name='mesh override y0')
            client.select('mesh override y0')
            client.set('x', 0.0); client.set('y', 0.0)
            client.set('x min', -bound); client.set('x max', bound)
            client.set('y min', 0.0); client.set('y max', 0.0)
            client.set('z min', monitor_z_min); client.set('z max', monitor_z_max)
            client.set('dx', dx); client.set('dy', dx); client.set('dz', dx)
            client.set('override x mesh', True)
            client.set('override y mesh', True)
            client.set('override z mesh', True)
            client.set('set equivalent index', True)
            client.set('equivalent x index', 2.0)
            client.set('equivalent y index', 1.0)
            client.set('equivalent z index', 2.0)

        client.save(save_path)
    finally:
        client.close()
    return
