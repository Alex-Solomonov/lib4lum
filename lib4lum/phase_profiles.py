from .dependencies import *

def _make_grid(size: int, period: float) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Symmetric (2*size+1)x(2*size+1) coordinate grid centered at origin.
    Args:
        size: Number of points from center to edge.
        period: Lattice period in meters.

    Returns:
        (x, X, Y) where x is the 1D axis and X, Y are 2D meshgrids.
    """
    x = np.linspace(-size*period, size*period, 2*size + 1)
    X, Y = np.meshgrid(x, x)
    return X, Y


def lens_profile(F: float, wl: float, period: float, size: int) -> npt.NDArray[np.float64]:
    """Computes 2D phase profile of a lens from Fermat's principle.
    Args:
        F: Focal distance in meters.
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        size: Number of points from center to edge.

    Returns:
        A numpy array of shape (2*size+1, 2*size+1) containing the phase.
    """
    X, Y = _make_grid(size, period)
    phase = -(np.sqrt(X**2 + Y**2 + F**2) - F)*2*np.pi/wl
    return phase, X, Y

def deflector_profile(theta_x: float, theta_y: float, wl: float, period: float, size: int) -> npt.NDArray[np.float64]:
    """Computes 2D linear phase profile of a beam deflector.
    Phase ramp: phi(x, y) = -(2*pi/wl) * (x*sin(theta_x) + y*sin(theta_y)).
    Args:
        theta_x: Deflection angle along x in radians.
        theta_y: Deflection angle along y in radians.
        wl: Operating wavelength in meters.
        period: Lattice period in meters.
        size: Number of points from center to edge.

    Returns:
        A numpy array of shape (2*size+1, 2*size+1) containing the phase.
    """
    _, X, Y = _make_grid(size, period)
    phase = -(X*np.sin(theta_x) + Y*np.sin(theta_y))*2*np.pi/wl
    return phase

def binarize(phase: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Binarizes phase to {0, pi}.
    Args:
        phase: Phase array.

    Returns:
        A numpy array with values 0 or pi.
    """
    phase = np.angle(np.exp(1j*phase))
    return np.where(phase >= 0, np.pi, 0.)

def quantize(phase: npt.NDArray[np.float64], n_levels: int) -> npt.NDArray[np.float64]:
    """Quantizes phase to N evenly-spaced levels in [0, 2*pi).

    Levels are at 0, 2*pi/N, 4*pi/N, ..., 2*pi*(N-1)/N.
    Phase is wrapped to [0, 2*pi) and rounded to nearest level (cyclic boundary).

    Args:
        phase: Phase array.
        n_levels: Number of quantization levels (>= 2).

    Returns:
        Array with values from {0, 2*pi/N, ..., 2*pi*(N-1)/N}.
    """
    if n_levels < 2:
        raise ValueError(f"n_levels must be >= 2; got {n_levels}")
    step = 2*np.pi / n_levels
    shifted = np.mod(phase + step/2, 2*np.pi)
    return (shifted // step) * step


### !!!TODO!!! Need normal interpolation method
### Right now magic numbers
def get_radii(phase : npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    phase_func = interpolate.interp1d([0, np.pi], [1.17004778e-07, 1.62533128e-07], fill_value = 'extrapolate')
    return phase_func(phase)



if __name__ == '__main__':
    WL = 850e-9
    PERIOD = 425e-9
    H_DISK = 150e-9
    H_SPACER = 38e-9
    SUBSTRATE_N = 1.5
    SIZE = 10                # 21x21 array (aperture 8.93 um)

    phase, X, Y = lens_profile(F=4e-06, wl=WL, period=PERIOD, size=SIZE)
    phase = quantize(phase, 2)
    radii_arr = get_radii(phase)
    print(radii_arr)
