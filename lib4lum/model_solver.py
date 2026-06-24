from .dependencies import *

MONITORS = ('Monitor X', 'Monitor Y', 'Monitor Z')


def default_processes() -> int:
    """
    half the logical CPU cores,
    the FDTD memory-bandwidth limit
    """
    return max(1, (cpu_count(logical=False) or 2) // 2)


def _extract(client, monitors) -> dict:
    """Complex \vec E, and |E|^2, and  axes per present monitor; silently skip absent ones"""
    out = {}
    for name in monitors:
        key = name.replace(' ', '_')
        try:
            out[f'{key}_E2'] = np.squeeze(client.getelectric(name))
            out[f'{key}_Ex'] = np.squeeze(client.getdata(name, 'Ex'))
            out[f'{key}_Ey'] = np.squeeze(client.getdata(name, 'Ey'))
            out[f'{key}_Ez'] = np.squeeze(client.getdata(name, 'Ez'))
            out[f'{key}_x'] = np.squeeze(client.getdata(name, 'x'))
            out[f'{key}_y'] = np.squeeze(client.getdata(name, 'y'))
            out[f'{key}_z'] = np.squeeze(client.getdata(name, 'z'))
        except Exception as exc:
            if 'does not exist' not in str(exc).lower():
                print(f'  WARN: monitor {name!r}: {exc}', flush=True)
    return out


def solve_model(fsp_path: str | Path, solved_path: str | Path | None = None, 
                processes: int | None = None, hide: bool = True, monitors: tuple = MONITORS) -> dict:
    """Solve a .fsp with native multi-process FDTD; return {key: array}.
    Args:
        fsp_path: The (clean) .fsp to solve.
        solved_path: If given, save the solved .fsp (with field data) there.
        processes: FDTD processes. None -> physical cores // 2.
        hide: Run headless.
        monitors: Monitor names to extract.

    Returns:
        {key: array} per monitor: complex Ex, Ey, Ez; |E|^2 + axes per present monitor.
    """
    if processes is None:
        processes = default_processes()
    client = lumapi.FDTD(str(fsp_path), hide=hide)
    try:
        try:
            client.setresource('FDTD', 1, 'processes', int(processes))
        except Exception as exc:  # older versions / license without multi-process
            print(f'  WARN: setresource processes={processes} rejected ({exc}); '
                  f'using engine default', flush=True)
        client.run()
        if solved_path is not None:
            solved_path = Path(solved_path)
            solved_path.parent.mkdir(parents=True, exist_ok=True)
            client.save(str(solved_path))
        return _extract(client, monitors)
    finally:
        client.close()


def solve_model_set(clean_dir: str | Path, solved_dir: str | Path | None = None,
                    results_dir: str | Path | None = None, save_solved: bool = True, 
                    processes: int | None = None, hide: bool = True, 
                    monitors: tuple = MONITORS, overwrite: bool = False) -> None:
    """Solve every .fsp in clean_dir -> solved .fsp in solved_dir + complex-E/|E|^2 .npz in results_dir.

    Args:
        clean_dir: Directory of built (unsolved) .fsp files.
        solved_dir: Where to save solved .fsp. None -> clean_dir.parent/'solved'.
        results_dir: Where to write <stem>.npz (complex E + |E|^2 per monitor).
            None -> clean_dir.parent/'results'.
        save_solved: Save the (large) solved .fsp. False -> results only.
        processes: FDTD processes. None -> physical cores // 2.
        hide: Run headless.
        monitors: Monitor names to extract.
        overwrite: Re-solve even if the .npz already exists.

    Returns:
        None.
    """
    if processes is None:
        processes = default_processes()
    
    clean_dir = Path(clean_dir)
    solved_dir = Path(solved_dir) if solved_dir is not None else clean_dir.parent / 'solved'
    results_dir = Path(results_dir) if results_dir is not None else clean_dir.parent / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)

    fsps = sorted(clean_dir.glob('*.fsp'))
    print(f'solve_model_set: {len(fsps)} models, processes={processes}', flush=True)
    for fsp in tqdm(fsps):
        out_npz = results_dir / (fsp.stem + '.npz')
        if out_npz.exists() and not overwrite: # prevents recalculation without removing original models
            continue
        solved_path = (solved_dir / fsp.name) if save_solved else None
        fields = solve_model(fsp, solved_path=solved_path, processes=processes, hide=hide, monitors=monitors)
        np.savez_compressed(out_npz, **fields)
