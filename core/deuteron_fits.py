"""Fit to Deuteron Lineshape NMR Signal

Translated from original C code by C. Dulya into Python by J. Maxwell in 2021.
"A line-shape analysis for spin-1 NMR signals", C. Dulya et. al.,
SMC Collaboration, NIM A 398 (1997) 109-125.

Complex lineshape based on:
"Measurement of complex RF susceptibility using a series Q-meter",
Yu.F. Kisselev, C.M. Dulya, T.O. Niinikoski, NIM A 354 (1995) 249-261.

And: "Complex deuteron NMR signals", M. McClellan,
Eur. Phys. J. A 61, 176 (2025).

Three public fitting functions are provided:

    fit(freqs, signal, initial_params)
        Absorption-only fit. Parameters: A, G, r, wQ, wL, eta, xi.

    fit_complex(freqs, signal, initial_params)
        Absorption + dispersion mixed by a phase angle. Adds: phase (in radians).

    fit_complex_cubic(freqs, signal, initial_params)
        Complex lineshape with cubic polynomial baseline. Adds: c3, c2, c1, c0.

All three return an lmfit result object.

Parameter bounds and other constraints are set by passing a dict-of-dicts as
initial_params, using lmfit's per-parameter format:

    initial_params = {
        'A':  {'value': 0.5, 'min': 0.0, 'max': 1.0},
        'wQ': {'value': 1e5, 'min': 0.0},
        'G':  1.0,   # plain scalar, no bounds
    }

Any parameter can mix a plain scalar (unconstrained) with a dict (constrained).
See lmfit documentation for additional options such as 'vary' and 'expr'.
"""

import numpy as np
from lmfit import Model


# --- Public fitting functions ------------------------------------------------

def fit(freqs, signal, initial_params):
    """Fit to deuteron lineshape.

    Args:
        freqs: list of frequencies
        signal: list of signal points
        initial_params: dict (A, G, r, wQ, wL, eta, xi)

    Returns:
        result object from lmfit
    """
    mod = Model(_fit_func)
    params = mod.make_params(**initial_params)
    return mod.fit(signal, params=params, w=freqs)


def fit_complex(freqs, signal, initial_params):
    """Fit to complex deuteron lineshape (absorption + dispersion mixed by phase).

    Args:
        freqs: list of frequencies
        signal: list of signal points
        initial_params: dict (A, G, r, wQ, wL, eta, xi, phase)

    Returns:
        result object from lmfit
    """
    mod = Model(_fit_func_complex)
    params = mod.make_params(**initial_params)
    return mod.fit(signal, params=params, w=freqs)


def fit_complex_cubic(freqs, signal, initial_params):
    """Fit to complex deuteron lineshape with cubic polynomial baseline.

    Args:
        freqs: list of frequencies
        signal: list of signal points
        initial_params: dict (A, G, r, wQ, wL, eta, xi, phase, c3, c2, c1, c0)

    Returns:
        result object from lmfit
    """
    mod = Model(_fit_func_complex_cubic)
    params = mod.make_params(**initial_params)
    return mod.fit(signal, params=params, w=freqs)


# --- Private model functions -------------------------------------------------

def _fit_func(w, A, G, r, wQ, wL, eta, xi):
    """Absorption-only deuteron lineshape evaluated at frequencies w."""
    R = (w - wL) / (3 * wQ)

    Ip = _iplus(r, wQ / wL, R)
    Im = _iminus(r, wQ / wL, R)

    Fm = _f(R, A, -1, eta)
    Fp = _f(R, A, 1, eta)

    Fm /= wQ
    Fp /= wQ

    F = G * (Im * Fm + Ip * Fp)
    fAsym = 1 + 0.5 * xi * (1 + R)
    bg = 0

    return fAsym * F + bg


def _fit_func_complex(w, A, G, r, wQ, wL, eta, xi, phase):
    """Complex deuteron lineshape: absorption and dispersion mixed by phase angle."""
    R = (w - wL) / (3 * wQ)

    Ip = _iplus(r, wQ / wL, R)
    Im = _iminus(r, wQ / wL, R)

    Fm_abs = _f(R, A, -1, eta)
    Fp_abs = _f(R, A, 1, eta)
    Fm_disp = _f(R, A, -1, eta, disp=True)
    Fp_disp = _f(R, A, 1, eta, disp=True)

    Fm_abs /= wQ
    Fp_abs /= wQ
    Fm_disp /= wQ
    Fp_disp /= wQ

    absorption = G * (Im * Fm_abs + Ip * Fp_abs)
    dispersion = G * (Im * Fm_disp + Ip * Fp_disp)

    fAsym = 1 + 0.5 * xi * (1 + R)
    bg = 0

    return fAsym * (np.cos(phase) * absorption + np.sin(phase) * dispersion) + bg


def _fit_func_complex_cubic(w, A, G, r, wQ, wL, eta, xi, phase, c3, c2, c1, c0):
    """Complex deuteron lineshape plus cubic polynomial baseline."""
    signal = _fit_func_complex(w, A, G, r, wQ, wL, eta, xi, phase)
    baseline = c3 * w**3 + c2 * w**2 + c1 * w + c0
    return signal + baseline


# --- Private math primitives -------------------------------------------------

def _iplus(r, Q, R):
    """Boltzmann population factor for the +1 quadrupole transition."""
    r3QR = r ** (-3 * Q * R)
    NN = r * (r + r3QR) + 1
    return r * (r - r3QR) / NN


def _iminus(r, Q, R):
    """Boltzmann population factor for the -1 quadrupole transition."""
    r3QR = r ** (3 * Q * R)
    NN = r * (r + r3QR) + 1
    return (r * r3QR - 1) / NN


def _f(R, A, eps, eta, disp=False):
    """Powder-averaged lineshape via Romberg quadrature over phi."""
    if eta < 0.001:
        FF = _integrals(R, A, eps, 3, 0, disp)
    else:
        FF = 0
        dphi = 1

        for i in (0, 1):
            ec2p = eta * np.cos(np.pi * dphi * i)
            Y2 = 3 - ec2p
            Y = np.sqrt(Y2)
            FF += 0.5 * np.sqrt(3) / Y * _integrals(R, A, eps, Y2, 0, disp)

        order = 5
        for N in [2 ** n for n in range(2, order + 1)]:
            dphi = 1 / N

            for i in range(N - 1, 0, -2):
                ec2p = eta * np.cos(np.pi * dphi * i)
                Y2 = 3 - ec2p
                Y = np.sqrt(Y2)
                FF += np.sqrt(3) / Y * _integrals(R, A, eps, Y2, ec2p, disp)

        FF *= dphi

    return FF


def _integrals(R, A, eps, Y2, etac2p, disp=False):
    """Single-orientation Dulya integrand for absorption or dispersion."""
    Y = np.sqrt(Y2)
    Yx2 = 2 * Y
    z2 = 1 - eps * R - etac2p
    q4 = z2 * z2 + A * A
    q2 = np.sqrt(q4)
    qq = np.sqrt(q2)

    cosa = z2 / q2
    cosa_2 = 1 / np.sqrt(2) * np.sqrt(1 + cosa)
    sina_2 = 1 / np.sqrt(2) * np.sqrt(1 - cosa)

    fTmp = Y2 + q2
    fVal = Yx2 * qq * cosa_2

    if disp:
        T = sina_2 * (np.pi / 2 + np.arctan((Y2 - q2) / (Yx2 * qq * sina_2)))
        L = -0.5 * cosa_2 * np.log((fTmp + fVal) / (fTmp - fVal))
        return (T + L) / (np.pi * qq)
    else:
        T = cosa_2 * (np.pi / 2 + np.arctan((Y2 - q2) / (Yx2 * qq * sina_2)))
        L = 0.5 * sina_2 * np.log((fTmp + fVal) / (fTmp - fVal))
        return (T + L) / (2 * qq)
