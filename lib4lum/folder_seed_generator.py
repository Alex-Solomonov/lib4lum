from pathlib import Path
from time import time
from numpy import random, zeros, savetxt

__all__ = 'generate_seed'

def generate_seed(eta : float = 0., realizations : int = 1) -> None:
    '''
    Generates and saves a set of random seeds for disorder realizations.
    The function creates a directory structure associated with the specified
    disorder magnitude (`eta`), generates a master random seed based on the
    current system time, and uses it to produce a collection of independent
    integer seeds. The generated seeds are stored in a text file named
    `!seeds.txt`, where the first line contains the disorder magnitude and
    the following lines contain the realization seeds. Generate folders
    named 'clean' and 'solved' for calculations.

    By default generate one seed with zero magintude (unpertubed case).

    Directory structure created:
    <project_root>/
        └── working space/
        └── models/
            └── eta_<eta>/
                └── clean/
                └── solved/
                !seeds.txt

    Args:
        eta: float
            Relative disorder magnitude (dimensionless).

        realizations: int
            Number of random seeds (disorder realizations) to generate.

    Returns:
        None

    '''
    GLOBAL_PATH = Path.cwd().parent
    MODELS_PATH = GLOBAL_PATH / 'models'
    SEED_PATH = MODELS_PATH / ('eta_' +str(eta))
    clean_path = SEED_PATH / 'clean'
    solved_path = SEED_PATH / 'solved'

    clean_path.mkdir(parents = True, exist_ok = True)
    solved_path.mkdir(parents = True, exist_ok = True)
    
    seed = int(time())
    rng = random.default_rng(seed)
    seed_realizations = rng.integers(low = 0, high = seed, size = (realizations, 1))

    saveseed_array = zeros([realizations+1, 1])
    saveseed_array[0] = eta
    saveseed_array[1:] = seed_realizations

    with open(SEED_PATH / '!seeds.txt', 'w') as file:
        savetxt(file, [eta], fmt = '%f')
        savetxt(file, seed_realizations, fmt = '%d')





