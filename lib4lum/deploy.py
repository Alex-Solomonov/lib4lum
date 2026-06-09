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
    _generate_config

def _generate_config() -> None:
    '''
    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    config = ConfigParser()
    config.add_section('SOLVER')
    config['SOLVER']['wavelength'] = '1e-09'

    config.add_section('BOX')
    config['BOX']['z_min'] = '-3e-09'

    config.add_section('MODEL')
    config['MODEL']['period'] = '425e-09'
    
    config.add_section('UNIT CELL')
    config['UNIT CELL']['h_disk'] = '150e-9'
    config['UNIT CELL']['h_spacer'] = '150e-9'
    

    with open(MODELS_PATH / 'model_config.ini', 'w') as config_file:
        config.write(config_file)

def read_config(config_path = None) -> dict:
    '''
    '''
    if config_path is None:
        GLOBAL_PATH = Path.cwd().parent
        MODELS_PATH = GLOBAL_PATH / 'models'
        config_path = MODELS_PATH / 'model_config.ini'

    config = ConfigParser()
    config.read(config_path)

    params = {
        section: {
            key: float(value)
            for key, value in config[section].items()
        }
        for section in config.sections()
    }

    return params