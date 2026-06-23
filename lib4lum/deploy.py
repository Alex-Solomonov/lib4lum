from pathlib import Path
from configparser import ConfigParser

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
    '''
    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    config = ConfigParser()

    config['SOLVER'] = {'wavelength': '850e-09'}
    config['STRUCTURE'] = {'size': '10', 'period': '425e-09', 'n_levels': '2'}
    config['UNIT CELL'] = {'h_disk': '150e-9', 'h_spacer': '38e-9'}
    config['MATERIALS'] = {'disk': 'Si (Silicon) - Palik', 'spacer': '1.5', 'substrate': '1.5'}
    config['BOX'] = {'z_min': '-3e-6', 'z_extent': '10e-6', 'mesh_accuracy': '3'}
    config['PROFILE'] = {'type': 'lens', 'focal_length': '4e-6'}
    config['RADII'] = {'radii': '1.17e-7, 1.62e-7'}

    with open(MODELS_PATH / 'default_model_config.ini', 'w') as config_file:
        config.write(config_file)

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

    radii = [float(r) for r in config['RADII']['radii'].split(',')]
    if len(radii) != params['STRUCTURE']['n_levels']:
        raise ValueError(
            f"[RADII] has {len(radii)} radii but [STRUCTURE] n_levels = "
            f"{params['STRUCTURE']['n_levels']}"
        )
    params['RADII']['radii'] = radii

    return params
