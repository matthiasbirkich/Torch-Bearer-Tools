"""Explicit photon/energy bands and horticultural ratios, no R dependency.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import math
import numpy as np

# Exact SI constants. Spectral input density stays per nm.
PHOTON_FACTOR = 1e6 / (6.62607015e-34 * 299792458.0 * 6.02214076e23)
BANDS = (
    ('PAR', 400, 700, 'PAR photons = PPFD; unweighted energy = PhR'),
    ('ePAR', 400, 750, 'Extended photon band, unconstrained'),
    ('FR_700_750', 700, 750, 'Far-red component of ePAR'),
    ('Blue_400_500', 400, 500, 'Explicit broad horticultural band'),
    ('Green_500_600', 500, 600, 'Explicit broad horticultural band'),
    ('Red_600_700', 600, 700, 'Explicit broad horticultural band'),
    ('Blue_Sellaro', 420, 490, 'Sellaro definition'),
    ('Green_Sellaro', 500, 570, 'Sellaro definition'),
    ('Red_Sellaro', 620, 680, 'Sellaro definition'),
    ('Red_Smith10', 655, 665, 'Smith 10 nm definition'),
    ('FarRed_Smith10', 725, 735, 'Smith 10 nm definition'),
    ('Red_Smith20', 650, 670, 'Smith 20 nm definition'),
    ('FarRed_Smith20', 720, 740, 'Smith 20 nm definition'),
    ('Red_Inada', 600, 700, 'Inada definition'),
    ('FarRed_Inada', 700, 800, 'Inada definition'),
    ('VIS_380_780', 380, 780, 'Explicit visible band, no photopic weighting'),
    ('UVA_CIE', 315, 400, 'Full UV-A, requires coverage from 315 nm'),
    ('UVA1', 340, 400, 'UV-A1 only, not full UV-A'),
    ('UVA2', 315, 340, 'UV-A2, requires coverage from 315 nm'),
    ('UVB_CIE', 280, 315, 'UV-B, requires coverage from 280 nm'),
    ('NIR_780_1000_partial', 780, 1000, 'Partial near-infrared, not full NIR'),
)
RATIOS = (
    ('FR_700_750_over_ePAR', 'FR_700_750', 'ePAR'),
    ('FR_700_750_over_PAR', 'FR_700_750', 'PAR'),
    ('Blue_400_500_over_PAR', 'Blue_400_500', 'PAR'),
    ('Green_500_600_over_PAR', 'Green_500_600', 'PAR'),
    ('Red_600_700_over_PAR', 'Red_600_700', 'PAR'),
    ('R_FR_Smith10', 'Red_Smith10', 'FarRed_Smith10'),
    ('R_FR_Smith20', 'Red_Smith20', 'FarRed_Smith20'),
    ('R_FR_Sellaro', 'Red_Sellaro', 'FR_700_750'),
    ('R_FR_Inada', 'Red_Inada', 'FarRed_Inada'),
    ('B_G_Sellaro', 'Blue_Sellaro', 'Green_Sellaro'),
)
SOURCE_XPAR = 'https://github.com/aphalo/photobiologyPlants/blob/b4934aab4517906a832693a0335ed4284735d2f9/R/plant-q-irrads.r'


def validate_hours(value):
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 24:
        raise ValueError('Photoperiod must be finite and between 0 and 24 hours/day.')
    return value


def calculate_photobiology(x, y, integrator, photoperiod_hours=None, invalid_reason=None):
    """Called after spectrum validation; invalid_reason yields an empty schema."""
    hours = validate_hours(photoperiod_hours)
    result = {
        'bands': {}, 'ratios': {}, 'par_umol_m2_s': None,
        'epar_umol_m2_s': None, 'xpar_umol_m2_s': None,
        'phr_W_m2': None, 'epar_unweighted_irradiance_W_m2': None,
        'xpar_fr_cap_applied': None,
        'dli_estimate': {'photoperiod_hours': hours, 'PAR_mol_m2_day': None,
                         'ePAR_mol_m2_day': None, 'xPAR_mol_m2_day': None,
                         'status': invalid_reason or ('NOT_REQUESTED' if hours is None else 'PENDING'),
                         'assumption': 'Constant measured irradiance for the specified hours every day; not a time-series measurement.'},
        'methods': {'bands': 'Trapezoidal energy and photon integrals in nm; interpolate exact boundaries; require full band coverage.',
                    'photon': '1e6/(h*c*N_A) * integral(E_lambda * lambda_nm * 1e-9, d_lambda_nm)',
                    'energy': 'Unweighted integral(E_lambda, d_lambda_nm), W/m^2; PAR energy band called PhR.',
                    'xPAR': 'Q_PAR + min(Q_FR_700_750, 0.4 * Q_PAR); photobiologyPlants 0.6.2 definition.',
                    'ratios': 'Photon integrals, dimensionless; denominator zero or incomplete coverage -> null.',
                    'DLI_estimate': 'Q_umol_m2_s * photoperiod_hours * 3600 / 1e6',
                    'source_xPAR': SOURCE_XPAR},
    }
    specifications = list(BANDS)
    if len(x) >= 2:
        specifications.insert(0, ('Measured_range', float(x[0]), float(x[-1]), 'Only the measured wavelength interval'))
    for name, low, high, definition in specifications:
        entry = {'low_nm': low, 'high_nm': high, 'irradiance_W_m2': None,
                 'photon_irradiance_umol_m2_s': None, 'status': invalid_reason or 'RANGE_INCOMPLETE',
                 'definition': definition}
        if invalid_reason is None and x[0] <= low and x[-1] >= high:
            entry['irradiance_W_m2'] = integrator(x, y, low, high)
            entry['photon_irradiance_umol_m2_s'] = PHOTON_FACTOR * integrator(x, y * x * 1e-9, low, high)
            entry['status'] = 'OK'
        result['bands'][name] = entry
    def q(name):
        return result['bands'][name]['photon_irradiance_umol_m2_s']
    par, epar, fr = q('PAR'), q('ePAR'), q('FR_700_750')
    result.update(par_umol_m2_s=par, epar_umol_m2_s=epar,
                  phr_W_m2=result['bands']['PAR']['irradiance_W_m2'],
                  epar_unweighted_irradiance_W_m2=result['bands']['ePAR']['irradiance_W_m2'])
    if par is not None and fr is not None:
        result['xpar_umol_m2_s'] = float(par + min(fr, .4 * par))
        result['xpar_fr_cap_applied'] = bool(fr > .4 * par)
    for name, numerator, denominator in RATIOS:
        a, b = q(numerator), q(denominator)
        status = invalid_reason or ('RANGE_INCOMPLETE' if a is None or b is None else 'ZERO_DENOMINATOR' if b == 0 else 'OK')
        result['ratios'][name] = {'value': float(a/b) if status == 'OK' else None,
                                  'unit': '1', 'numerator_band': numerator,
                                  'denominator_band': denominator, 'status': status}
    if hours is not None and invalid_reason is None:
        for name, flux in [('PAR', par), ('ePAR', epar), ('xPAR', result['xpar_umol_m2_s'])]:
            result['dli_estimate'][name + '_mol_m2_day'] = None if flux is None else float(flux * hours * .0036)
        result['dli_estimate']['status'] = 'ESTIMATE_CONSTANT_IRRADIANCE' if par is not None and epar is not None else 'RANGE_INCOMPLETE'
    return result
