from pathlib import Path
from configparser import ConfigParser

def run(**kwargs) -> None:
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
    _generate_config(**kwargs)

def _generate_config(**kwargs) -> None:
    '''
    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    config = ConfigParser()
    config.add_section('BOX')
    config['BOX']['xy_min'] = '-1e-09'
    config['BOX']['xy_max'] = '1e-09'
    config['BOX']['z_min'] = '-1e-09'
    config['BOX']['z_max'] = '1e-09'

    config.add_section('SOLVER')
    config['SOLVER']['mesh_dx'] = '1e-09'
    config['SOLVER']['mesh_dy'] = '1e-09'
    config['SOLVER']['mesh_dz'] = '1e-09'

    config.add_section('SOURCE')
    config['SOURCE']['wavelength'] = '500e-09'
    config['SOURCE']['span'] = '250e-09'
    config['SOURCE']['polarization'] = 'x'
    config['SOURCE']['direction'] = 'FWD'
    config['SOURCE']['position'] = '-1e-09'

    config.add_section('STRUCTURE')
    config['STRUCTURE']['size'] = '12'
    config['STRUCTURE']['period'] = '425e-09'
    
    config.add_section('UNIT')
    config['UNIT']['height'] = '1e-09'

    with open(MODELS_PATH / 'default_model_config.ini', 'w') as config_file:
        config.write(config_file)

def _parse_dict_value(value):
    try:
        return(int(value))
    except:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def read_config(config_path : Path | str = None, config_name : str = None) -> dict:
    '''
    '''

    if config_path is None:
        global_path = Path.cwd().parent
        config_path = global_path / 'models'
    else:
        config_path = Path(config_path)

    if config_name is None:
        config_name = config_path / 'default_model_config.ini'

    full_path = config_path / config_name

    config = ConfigParser()
    config.read(full_path)

    params = {
        section: {
            key: _parse_dict_value(value)
            for key, value in config[section].items()
        }
        for section in config.sections()
    }

    return params

params = read_config()