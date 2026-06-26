from pathlib import Path
from configparser import ConfigParser
from collections.abc import Iterable


_DEFAULTS: dict[str, dict[str, str]] = {
    'SOLVER':    {'wavelength': '850e-09'},
    'STRUCTURE': {'size': '10', 'period': '425e-09', 'n_levels': '2'},
    'UNIT CELL': {'h_disk': '150e-9', 'h_spacer': '38e-9'},
    'MATERIALS': {'disk': 'Si (Silicon) - Palik', 'spacer': '1.5', 'substrate': ''},
    'BOX':       {'z_min': '-3e-6', 'z_extent': '10e-6', 'mesh_accuracy': '3'},
    'PROFILE':   {'type': 'lens', 'focal_length': '4e-6', 'theta_x': '0.0', 'theta_y': '0.0'},
    'RADII':     {'radii': ''},
}


def _set_seed(config_path: str | Path, seed: int | None = None, radii: Iterable[float] | None = None) -> None:
    config = ConfigParser()
    config.read(config_path)
    if seed is not None:
        if not config.has_section('PROFILE'):
            config.add_section('PROFILE')
        config['PROFILE']['seed'] = str(int(seed))
    if radii is not None:
        if not config.has_section('RADII'):
            config.add_section('RADII')
        config['RADII']['radii'] = ', '.join(f'{r:.6e}' for r in radii)
    with open(config_path, 'w') as config_file:
        config.write(config_file)

def write_config(config_path: str | Path, **values: float | int | str | Iterable[float]) -> None:
    '''Write a model config .ini, routing flat keyword values to their [SECTION].

    The schema (sections + keys) lives once in _DEFAULTS, so this writer and
    read_config can never drift. Pass any subset of options as keywords; unprovided
    ones keep their _DEFAULTS value. Omit 'seed' to let generate_model create one.

    Args:
        config_path: Destination .ini (parent dirs are created).
        **values: Config options keyed by ini name (section in brackets):
            wavelength [SOLVER]; size, period, n_levels [STRUCTURE];
            h_disk, h_spacer [UNIT CELL]; disk, spacer, substrate [MATERIALS];
            z_min, z_extent, mesh_accuracy [BOX];
            type, focal_length, theta_x, theta_y, seed [PROFILE];
            radii [RADII] -- a float iterable (-> comma list) or a string.

    Raises:
        KeyError: If a key is not a recognised config option.
    '''
    section_of = {key: section for section, keys in _DEFAULTS.items() for key in keys}
    overrides: dict[str, dict] = {}
    for key, value in values.items():
        if key not in section_of:
            raise KeyError(f"unknown config key {key!r}; valid keys: {sorted(section_of)}")
        if key == 'radii' and not isinstance(value, str):
            value = ', '.join(f'{x:.6e}' for x in value)
        overrides.setdefault(section_of[key], {})[key] = value

    config = ConfigParser()
    for section, defaults in _DEFAULTS.items():
        merged = dict(defaults)
        merged.update({key: str(value) for key, value in overrides.get(section, {}).items()})
        config[section] = merged
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as config_file:
        config.write(config_file)


def run() -> None:
    '''
    Initializes the project directory structure.
    The function determines the project's root directory as the parent
    of the current working directory and creates a models directory
    inside it if it does not already exist.
    Directory structure:

        <project_root>/
        └── working space/
            └── example.py
            └── example.ipynb
        └── models/

    Args:
        None

    Returns:
        None
    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    MODELS_PATH.mkdir(parents = True, exist_ok = True)
    _generate_config()

def _generate_config() -> None:
    '''Write the default model config to models/default_model_config.ini.'''
    write_config(Path.cwd().parent / 'models' / 'default_model_config.ini')

def _coerce(value: str) -> float | str:
    '''
    Parse config values cleanly
    '''
    try:
        return float(value)
    except ValueError:
        return value.strip()

def read_config(config_path: str | Path | None = None) -> dict:
    '''
    Read the model config into a nested {section: {key: value}} dict.

    Numeric values become floats; STRUCTURE.size / n_levels are ints;
    PROFILE.type stays a string; RADII.radii is parsed to a list[float].

    Args:
        config_path: Path to the .ini. None -> models/default_model_config.ini
            (cwd-relative, matching run()).

    Returns:
        The parsed config.

    Raises:
        ValueError: If the number of [RADII] radii != STRUCTURE.n_levels.
    '''
    if config_path is None:
        GLOBAL_PATH = Path.cwd().parent
        MODELS_PATH = GLOBAL_PATH / 'models'
        config_path = MODELS_PATH / 'default_model_config.ini'

    config = ConfigParser()
    config.read(config_path)

    params = {
        section: {
            key: _coerce(value)
            for key, value in config[section].items()
        }
        for section in config.sections()
    }
    params['STRUCTURE']['size'] = config.getint('STRUCTURE', 'size')
    params['STRUCTURE']['n_levels'] = config.getint('STRUCTURE', 'n_levels')
    params['PROFILE']['seed'] = config.getint('PROFILE', 'seed', fallback=None)

    radii = config.get('RADII', 'radii', fallback='').strip()
    if radii:
        radii = [float(r) for r in radii.split(',')]
        if len(radii) != params['STRUCTURE']['n_levels']:
            raise ValueError(
                f"[RADII] has {len(radii)} radii but [STRUCTURE] n_levels = "
                f"{params['STRUCTURE']['n_levels']}"
            )
        params['RADII']['radii'] = radii
    else:
        params['RADII']['radii'] = None
    substrate = config.get('MATERIALS', 'substrate', fallback='').strip()
    params['MATERIALS']['substrate'] = float(substrate) if substrate else None

    return params
