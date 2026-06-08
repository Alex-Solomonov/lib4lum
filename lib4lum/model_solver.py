from .dependencies import *

MONITORS = ('Monitor X', 'Monitor Y', 'Monitor Z')


def default_processes() -> int:
    """
    half the logical CPU cores,
    the FDTD memory-bandwidth limit
    """
    return max(1, (cpu_count(logical=False) or 2) // 2)


def _extract(client, monitors) -> dict:
    """|E|^2 + axes per present monitor; silently skip absent ones"""
    out = {}
    for name in monitors:
        key = name.replace(' ', '_')
        try:
            out[f'{key}_E2'] = np.squeeze(client.getelectric(name))
            out[f'{key}_x'] = np.squeeze(client.getdata(name, 'x'))
            out[f'{key}_y'] = np.squeeze(client.getdata(name, 'y'))
            out[f'{key}_z'] = np.squeeze(client.getdata(name, 'z'))
        except Exception as exc:
            if 'does not exist' not in str(exc).lower():
                print(f'  WARN: monitor {name!r}: {exc}', flush=True)
    return out


def solve_model(fsp_path, processes=None, hide=True, monitors=MONITORS) -> dict:
    """Solve a .fsp with native multi-process FDTD; return {key: array}."""
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
        return _extract(client, monitors)
    finally:
        client.close()


def solve_model_set(processes=None, hide=True, monitors=MONITORS, overwrite=False) -> None:
    """Solve every clean/*.fsp under models/eta_*/ -> solved/<seed>.npz.

    Same cwd-relative layout as generate_model_set (Path.cwd().parent/'models').
    Set overwrite=True to re-solve existing results.
    """
    if processes is None:
        processes = default_processes()
    print(f'solve_model_set: processes={processes} (os.cpu_count={os.cpu_count()})', flush=True)

    MODELS_PATH = Path.cwd().parent / 'models'
    folder_list = [x for x in MODELS_PATH.iterdir() if x.is_dir()]

    for folder_path in folder_list:
        clean_path = folder_path / 'clean'
        solved_path = folder_path / 'solved'
        solved_path.mkdir(parents=True, exist_ok=True)
        fsps = sorted(clean_path.glob('*.fsp'))
        print(f'Solving {folder_path.name}: {len(fsps)} models', flush=True)
        for fsp in tqdm(fsps):
            out_npz = solved_path / (fsp.stem + '.npz')
            if out_npz.exists() and not overwrite:
                continue
            fields = solve_model(fsp, processes=processes, hide=hide, monitors=monitors)
            np.savez_compressed(out_npz, **fields)
