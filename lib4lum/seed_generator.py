from time import time
from numpy import random, int_
import numpy.typing as npt


__all__ = ('generate_seeds',)


def generate_seeds(n: int, master: int | None = None) -> npt.NDArray[int_]:
    '''Generate n integer seeds for a batch of random-profile realizations.

    Each seed feeds one config's [PROFILE] seed, so the batch reproduces from the
    written configs -- or deterministically from `master` if you pass one.

    Args:
        n: Number of seeds to generate.
        master: Master seed for the generator. None -> time-seeded (fresh each call).

    Returns:
        n seeds as a 1-D int array.
    '''
    if master is None:
        master = int(time())
    return random.default_rng(master).integers(0, 2**63 - 1, size=n) # 128 bit
