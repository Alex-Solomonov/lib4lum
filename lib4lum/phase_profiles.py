from .dependencies import *


def make_grid(size: int, period: float) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Symmetric (2*size+1) x (2*size+1) coordinate grid centred at the origin.

    Args:
        size: Number of cells from the centre to the edge.
        period: Lattice period in meters.

    Returns:
        (X, Y) meshgrids, each of shape (2*size+1, 2*size+1), in meters.
    """
    x = np.linspace(-size * period, size * period, 2 * size + 1)
    return np.meshgrid(x, x)


def quantize(phase: npt.NDArray[np.float64], n: int) -> npt.NDArray[np.int_]:
    """Quantise continuous phase to a quasi-phase map of level indices in [0, n).

    Wraps the phase into [0, 2*pi) and rounds to the nearest of n evenly-spaced
    levels (cyclic boundary), returning the integer level index per pixel.

    Args:
        phase: Continuous phase in radians.
        n: Number of quantisation levels; must be an integer >= 2.

    Returns:
        Integer array of the same shape as `phase`, with values in [0, n).

    Raises:
        ValueError: If `n` is not an integer, or is < 2.
    """
    if not isinstance(n, (int, np.integer)) or n < 2:
        raise ValueError(f"Got {n!r} instead of an integer n > 1")
    step = 2 * np.pi / n
    return (np.mod(phase + step / 2, 2 * np.pi) // step).astype(int) % n


def lens_profile(F: float, wl: float, period: float, size: int, n: int) -> npt.NDArray[np.int_]:
    """Quasi-phase map of a focusing lens (Fermat), quantised to n levels.

    Args:
        F: Focal length in meters.
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        size: Number of cells from the centre to the edge.
        n: Number of quantisation levels (>= 2).

    Returns:
        Integer quasi-phase map of shape (2*size+1, 2*size+1), values in [0, n).
    """
    X, Y = make_grid(size, period)
    phase = -(np.sqrt(X**2 + Y**2 + F**2) - F) * 2 * np.pi / wl
    return quantize(phase, n)


def deflector_profile(theta_x: float, theta_y: float, wl: float, period: float, size: int, n: int) -> npt.NDArray[np.int_]:
    """Quasi-phase map of a linear-ramp beam deflector, quantised to n levels.

    Phase ramp: phi(x, y) = -(2*pi/wl) * (x*sin(theta_x) + y*sin(theta_y)).

    Args:
        theta_x: Deflection angle along x in radians.
        theta_y: Deflection angle along y in radians.
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        size: Number of cells from the centre to the edge.
        n: Number of quantisation levels (>= 2).

    Returns:
        Integer quasi-phase map of shape (2*size+1, 2*size+1), values in [0, n).
    """
    X, Y = make_grid(size, period)
    phase = -(X * np.sin(theta_x) + Y * np.sin(theta_y)) * 2 * np.pi / wl
    return quantize(phase, n)


def random_profile(n: int, size: int, seed: int) -> npt.NDArray[np.int_]:
    """Quasi-phase map with a seeded-random level index at each pixel.

    Args:
        n: Number of levels; each pixel draws an int in [0, n).
        size: Number of cells from the centre to the edge.
        seed: Seed for np.random.default_rng; the same seed reproduces the map.

    Returns:
        Integer quasi-phase map of shape (2*size+1, 2*size+1), values in [0, n).
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, (2 * size + 1, 2 * size + 1))


def get_radii(quasi_map: npt.NDArray[np.int_], radii: list[float] | npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Map a quasi-phase map to physical radii by per-level lookup.

    Args:
        quasi_map: Integer level indices in [0, n).
        radii: The n radii in meters; radii[k] is used wherever quasi_map == k.

    Returns:
        Radius array in meters, of the same shape as `quasi_map`.
    """
    return np.asarray(radii, dtype=np.float64)[quasi_map]
