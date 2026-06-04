from .dependencies import *
from . import phase_profiles

def generate_model_set(N : int, 
                       F : float, 
                       wl : float,
                       period : float, 
                       size : int,
                       h_disk : float,
                       h_spacer : float,
                       substrate_n : float) -> None:
    '''
    Generates a set of disordered metasurface lens models for all available
    disorder realizations and saves them as simulation files.
    The function first computes the ideal (reference) lens geometry using
    `design_lens()`. It then scans all disorder directories in the `models\clean`
    folder, loads the corresponding disorder magnitude (`eta`) and realization
    seeds from `!seeds.txt`, and generates perturbed lens geometries by applying
    independent random radius variations within the range
    [(1 - eta) * r, (1 + eta) * r].
    Each perturbed structure is exported as an FDTD simulation model (`.fsp`)
    into the corresponding `clean` subdirectory.

    Args:
        N: int
            Number of discrete radius values used in the lens design.

        F: float
            Focal length of the metalens.

        wl: float
            Operating wavelength.

        period: float
            Lattice period of the metasurface.

        size: int
            Number of unit cells along one side of the lens.

        h_disk: float
            Height of the nanodisk resonators.

        h_spacer: float
            Thickness of the spacer layer.

        substrate_n: float
            Refractive index of the substrate material.

    Returns:
        None
    '''
    
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'  
    
    radii_etalon, X_etalon, Y_etalon = design_lens(N = N, F = F, wl = wl, period = period, size = size)
    folder_list = [x for x in MODELS_PATH.iterdir() if x.is_dir()]
    
    for folder_path in folder_list:
        clean_path = folder_path / 'clean'
        print('Reading {}'.format(folder_path))
        data = np.loadtxt(folder_path / '!seeds.txt')

        eta = data[0]
        seeds = data[1:]

        for seed in tqdm(seeds):
            rng = np.random.default_rng(int(seed))
            # (-eta, eta) -> 1+(-eta, eta)
            floating_error = rng.uniform(low = 1-eta, high = 1+eta, size = np.shape(radii_etalon))
            
            radii = floating_error * radii_etalon

            build_model(radii=radii, X = X_etalon, Y = Y_etalon, wl=wl, period=period,
                h_disk=h_disk, h_spacer=h_spacer, save_path=str(clean_path / (str(int(seed))+'.fsp')),
                substrate_n=substrate_n)


def design_lens(N : int, F : float, wl : float, period : float, size = int):
    '''
    Generates the discretized geometry of a metalens based on its target
    focal distance.
    The function computes the ideal lens phase distribution, quantizes it
    into a finite number of phase levels, and maps each quantized phase value
    to the corresponding resonator radius. The resulting radius grid and
    coordinate arrays define the lens layout.

    Args:
        N: float
            Number of discrete phase levels used for quantization.

        F: float
            Focal length of the lens.

        wl: float
            Operating wavelength.

        period: float
            Lattice period of the metasurface.

        size: int
            Number of unit cells along one side of the lens.

    Returns:
        radii_grid: 
            2D array of resonator radii corresponding to the
            quantized phase profile.

        X: 
            2D array of x-coordinates.
        Y: 
            2D array of y-coordinates.
    '''
    phase, X, Y = phase_profiles.lens_profile(F = F, wl = wl, period = period, size = size)
    phase_q = phase_profiles.quantize(phase, n_levels=N)
    radii_grid = phase_profiles.get_radii(phase_q)
    return radii_grid, X, Y

def build_model(
    radii: npt.NDArray[np.float64],
    X : npt.NDArray[np.float64],
    Y : npt.NDArray[np.float64],
    wl: float, period: float,
    h_disk: float, h_spacer: float,
    save_path: str,
    substrate_n: float | None = None,
    source_wl: float | None = None,
    source_span: float = 0.0,
    polarization: str = 'x',
    mesh_dx: float | None = None,
    monitor_z_min: float = -4e-06,
    monitor_z_max: float = 4e-06,
    monitor_z_focal: float | None = None,
    position_offsets: npt.NDArray[np.float64] | None = None,
    lateral_bound: float | None = None,
    refine_y0_plane: bool = False,
    refine_y0_dx_wl: float = 0.01,
) -> str:
    """Builds a Lumerical FDTD model from a precomputed radii grid.
    Args:
        radii: 2D array of disk radii in meters, shape (2*size+1, 2*size+1).
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        h_disk: Disk height in meters.
        h_spacer: Spacer height in meters.
        save_path: Path to save .fsp file.
        substrate_n: Substrate refractive index. None means no substrate.
        source_wl: Source wavelength. Defaults to wl.
        source_span: Source wavelength span.
        polarization: Source polarization. 'x', 'y', or 'xy'.
        mesh_dx: Mesh size. None means Lumerical default.
        monitor_z_min: Monitor and solver z min.
        monitor_z_max: Monitor and solver z max.
        monitor_z_focal: z position for transverse Monitor Z. None means skip Monitor Z.
        position_offsets: Per-pillar (dx, dy) displacements in meters; shape (n, n, 2).
            None -> use regular lattice positions (default; backward compatible).
            Used for positional-disorder ensembles per Wan et al. APL 2025 eq.P2.3/4
            (delta_x = Delta * xi * period, Delta ~ U[-0.5, 0.5]).
        lateral_bound: Half-width of the FDTD region in x and y (meters).
            None (default) uses (size+2)*period — keeps prior behavior.
            Larger values widen the vacuum margin between the lens edge and the
            lateral PMLs, mitigating PML-reflection artifacts at high NA.
        refine_y0_plane: If True, add a Lumerical mesh override on the y=0 plane
            (the Monitor Y slice) with cell size `refine_y0_dx_wl * wl` in all
            three directions and `set equivalent index` true (eq_x=eq_z=2,
            eq_y=1). Default False — keeps prior behavior. Useful at high NA to
            resolve the elongated Richards–Wolf focal spot along x: at NA ≈ 0.9
            and mesh_accuracy=3 default, FWHM_x is over-estimated by ~10% due to
            coarse cells on the y=0 diagnostic plane; refining there drops the
            measured FWHM_x / FWHM_y ratio from 1.75 to 1.60 for the F=2 µm
            binary Huygens lens.
        refine_y0_dx_wl: Mesh cell size in wavelength units when `refine_y0_plane`
            is True. Default 0.01 = wl/100 — matches the colleague's saved .fsp.

    Returns:
        The save_path.
    """
    if polarization not in ('x', 'y', 'xy'):
        raise ValueError(f"polarization must be 'x', 'y', or 'xy'; got {polarization!r}")

    n = radii.shape[0]
    size = (n - 1)//2
    # Grid
    if position_offsets is not None:
        if position_offsets.shape != (n, n, 2):
            raise ValueError(f"position_offsets must have shape ({n},{n},2); got {position_offsets.shape}")
        X += position_offsets[..., 0]
        Y += position_offsets[..., 1]
    bound = lateral_bound if lateral_bound is not None else (size + 2)*period

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

        # Structure groups — batched via Lumerical script (single IPC call)
        client.putv('X_arr', X.flatten())
        client.putv('Y_arr', Y.flatten())
        client.putv('R_arr', radii.flatten())
        client.putv('h_d', h_disk)
        client.putv('h_s', h_spacer)
        client.putv('N_sq', n*n)

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
        set("material", "Si (Silicon) - Palik");
        addtogroup("Bottom_disk");

        addcircle;
        set("x", X_arr(i)); set("y", Y_arr(i));
        set("z min", h_d); set("z max", h_d + h_s);
        set("radius", R_arr(i));
        set("name", "Spacer_" + num2str(i));
        set("index", 1.5);
        addtogroup("Spacer");

        addcircle;
        set("x", X_arr(i)); set("y", Y_arr(i));
        set("z min", h_d + h_s); set("z max", 2*h_d + h_s);
        set("radius", R_arr(i));
        set("name", "Top_disk_" + num2str(i));
        set("material", "Si (Silicon) - Palik");
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

        # Optional y=0 mesh override — refines FWHM_x sampling at high NA.
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