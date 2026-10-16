"""Photopic illuminance, conventional PPFD and CIE 1995 CRI.

Input: absolute spectral irradiance in W m^-2 nm^-1, no normalisation.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import csv
import json
from pathlib import Path
import warnings

import numpy as np
import colour

from photobiology_metrics import calculate_photobiology, validate_hours

H = 6.62607015e-34
C = 299792458.0
NA = 6.02214076e23
KM = 683.0
CRI_METHOD = 'CIE 1995'


def band_integral(wavelength_nm, spectral_values, low, high):
    """Trapezoidal integration in nm; interpolate exact band boundaries."""
    x = np.asarray(wavelength_nm, dtype=float)
    y = np.asarray(spectral_values, dtype=float)
    if x[0] > low or x[-1] < high:
        raise ValueError(f'Spectrum does not cover {low}-{high} nm.')
    inner = x[(x > low) & (x < high)]
    grid = np.concatenate(([low], inner, [high]))
    return float(np.trapezoid(np.interp(grid, x, y), grid))


def calculate_metrics(wavelength_nm, irradiance, wavelength_mapping_valid=True, photoperiod_hours=None):
    photoperiod_hours = validate_hours(photoperiod_hours)
    x = np.asarray(wavelength_nm, dtype=float)
    y = np.asarray(irradiance, dtype=float)
    result = {'input_unit': 'W/m^2/nm', 'colour_science_version': colour.__version__,
              'lux': None, 'ppfd_umol_m2_s': None, 'cri_Ra': None,
              'cri_Ri': {str(i): None for i in range(1, 15)},
              'cct_K': None, 'duv': None, 'cri_reference_delta_uv': None,
              'cri_valid': False, 'quality_flags': [], 'warnings': [],
              'methods': {'lux': '683 * integral(E_lambda * CIE 1924 V(lambda), 360..830 nm)',
                          'ppfd': '1e6/(h*c*N_A) * integral(E_lambda * lambda_m, 400..700 nm)',
                          'cri': 'CIE 13.3-1995; Ra = mean(R1..R8), R1..R14 exported',
                          'integration': 'Trapezoidal on wavelength in nm; input already per nm'},
              'constants': {'h_J_s': H, 'c_m_s': C, 'N_A_per_mol': NA, 'K_m_lm_W': KM}}
    result['photobiology'] = calculate_photobiology(x, y, band_integral, photoperiod_hours, 'INPUT_NOT_VALIDATED')
    if not wavelength_mapping_valid:
        result['photobiology'] = calculate_photobiology(x, y, band_integral, photoperiod_hours, 'WAVELENGTH_MAPPING_UNVERIFIED')
        result['quality_flags'].append('WAVELENGTH_MAPPING_UNVERIFIED')
        result['warnings'].append('Number of bins conflicts with the reported range; metrics not calculated.')
        return result
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) < 2:
        raise ValueError('At least two matching wavelength/irradiance points are required.')
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.any(np.diff(x) <= 0):
        raise ValueError('Input must be finite and wavelengths strictly increasing.')
    if np.any(y < 0):
        result['photobiology'] = calculate_photobiology(x, y, band_integral, photoperiod_hours, 'NEGATIVE_IRRADIANCE')
        result['quality_flags'].append('NEGATIVE_IRRADIANCE')
        result['warnings'].append('Negative irradiance found; raw data retained and metrics not calculated.')
        return result

    result['photobiology'] = calculate_photobiology(x, y, band_integral, photoperiod_hours)
    lef = colour.SDS_LEFS['CIE 1924 Photopic Standard Observer']
    low, high = float(lef.wavelengths[0]), float(lef.wavelengths[-1])
    if x[0] <= low and x[-1] >= high:
        grid = np.unique(np.concatenate((lef.wavelengths, x[(x >= low) & (x <= high)])))
        v = np.interp(grid, lef.wavelengths, lef.values)
        result['lux'] = float(KM * np.trapezoid(np.interp(grid, x, y) * v, grid))
    else:
        result['quality_flags'].append('LUX_RANGE_INCOMPLETE')

    try:
        # Integrate over nm: lambda itself converts to m, density stays per nm.
        # No additional 1e9 factor is needed or permitted.
        result['ppfd_umol_m2_s'] = 1e6 / (H * C * NA) * band_integral(x, y * x * 1e-9, 400., 700.)
    except ValueError as error:
        result['quality_flags'].append('PPFD_RANGE_INCOMPLETE')
        result['warnings'].append(str(error))

    if x[0] > 360 or x[-1] < 830:
        result['quality_flags'].append('CRI_RANGE_INCOMPLETE')
        return result
    if result['lux'] is None or result['lux'] <= 0:
        result['quality_flags'].append('CRI_NO_VISIBLE_SIGNAL')
        return result
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            sd = colour.SpectralDistribution(dict(zip(x, y)), name='Measured irradiance')
            # Same observer and shape as the library's CIE 1995 implementation.
            from colour.quality.cri import SPECTRAL_SHAPE_DEFAULT
            cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(SPECTRAL_SHAPE_DEFAULT)
            test_sd = sd.copy().align(cmfs.shape)
            XYZ = colour.sd_to_XYZ(test_sd, cmfs=cmfs)
            uv = colour.UCS_to_uv(colour.XYZ_to_UCS(XYZ))
            cct, duv = colour.temperature.uv_to_CCT_Robertson1968(uv)
            if not np.isfinite(cct) or not np.isfinite(duv) or cct <= 0:
                raise ValueError('No finite correlated colour temperature.')
            result['cct_K'], result['duv'] = float(cct), float(duv)
            if cct < 5000:
                reference = colour.sd_blackbody(cct, cmfs.shape)
            else:
                xy = colour.temperature.CCT_to_xy_CIE_D(cct)
                reference = colour.sd_CIE_illuminant_D_series(xy).align(cmfs.shape)
            ref_XYZ = colour.sd_to_XYZ(reference, cmfs=cmfs)
            ref_uv = colour.UCS_to_uv(colour.XYZ_to_UCS(ref_XYZ))
            delta_uv = float(np.linalg.norm(uv - ref_uv))
            result['cri_reference_delta_uv'] = delta_uv
            # CRI is not qualified for test light too far from its reference white.
            if delta_uv > .0054:
                result['quality_flags'].append('CRI_REFERENCE_DISTANCE_TOO_LARGE')
                result['warnings'].append('CRI omitted: reference chromaticity distance exceeds 0.0054.')
            else:
                spec = colour.colour_rendering_index(sd.copy(), additional_data=True, method=CRI_METHOD)
                ra = float(spec.Q_a)
                ri = {str(i): float(value.Q_a) for i, value in spec.Q_as.items()}
                if not np.isfinite(ra) or not all(np.isfinite(v) for v in ri.values()):
                    raise ValueError('Non-finite CRI result.')
                result['cri_Ra'] = ra
                result['cri_Ri'] = ri
                result['cri_valid'] = True
            result['warnings'].extend(str(w.message) for w in caught)
    except Exception as error:
        result['quality_flags'].append('CRI_CALCULATION_FAILED')
        result['warnings'].append(f'{type(error).__name__}: {error}')
    if not result['quality_flags']:
        result['quality_flags'].append('OK')
    return result


def csv_value(value, decimal_comma):
    if value is None:
        return ''
    if isinstance(value, float):
        text = repr(value)
        return text.replace('.', ',') if decimal_comma else text
    return value


def save_metrics(folder, metrics, metadata, decimal_comma=True):
    folder = Path(folder)
    row = {'timestamp_utc': metadata.get('measurement_timestamp_utc', metadata.get('started_utc', '')),
           'device_id': metadata.get('device_id', ''), 'sample_name': metadata.get('sample_name', ''),
           'exposure_time_ms': metadata.get('exposure_time_ms'), 'lux_lx': metrics['lux'],
           'PPFD_umol_m2_s': metrics['ppfd_umol_m2_s'], 'CRI_Ra_CIE1995': metrics['cri_Ra'],
           **{f'R{i}': metrics['cri_Ri'].get(str(i)) for i in range(1, 15)},
           'CCT_K': metrics['cct_K'], 'Duv': metrics['duv'],
           'cri_reference_delta_uv': metrics['cri_reference_delta_uv'],
           'cri_valid': metrics['cri_valid'], 'quality_flags': '|'.join(metrics['quality_flags'])}
    photo = metrics['photobiology']
    row.update(PAR_umol_m2_s=photo['par_umol_m2_s'], ePAR_umol_m2_s=photo['epar_umol_m2_s'],
               xPAR_umol_m2_s=photo['xpar_umol_m2_s'], PhR_400_700_W_m2=photo['phr_W_m2'],
               irradiance_400_750_W_m2=photo['epar_unweighted_irradiance_W_m2'],
               FR_700_750_umol_m2_s=photo['bands']['FR_700_750']['photon_irradiance_umol_m2_s'],
               xPAR_FR_cap_applied=photo['xpar_fr_cap_applied'],
               photoperiod_hours=photo['dli_estimate']['photoperiod_hours'],
               DLI_PAR_estimate_mol_m2_day=photo['dli_estimate']['PAR_mol_m2_day'],
               DLI_ePAR_estimate_mol_m2_day=photo['dli_estimate']['ePAR_mol_m2_day'],
               DLI_xPAR_estimate_mol_m2_day=photo['dli_estimate']['xPAR_mol_m2_day'],
               DLI_status=photo['dli_estimate']['status'])
    row.update({name: entry['value'] for name, entry in photo['ratios'].items()})
    with (folder / 'bands.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['band', 'low_nm', 'high_nm', 'irradiance_W_m2', 'photon_irradiance_umol_m2_s', 'status', 'definition'])
        for name, entry in photo['bands'].items():
            writer.writerow([name] + [csv_value(entry[key], decimal_comma) for key in
                ['low_nm', 'high_nm', 'irradiance_W_m2', 'photon_irradiance_umol_m2_s', 'status', 'definition']])
    with (folder / 'ratios.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['ratio', 'value', 'unit', 'numerator_band', 'denominator_band', 'status'])
        for name, entry in photo['ratios'].items():
            writer.writerow([name] + [csv_value(entry[key], decimal_comma) for key in
                ['value', 'unit', 'numerator_band', 'denominator_band', 'status']])
    with (folder / 'metrics.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(row.keys())
        writer.writerow([csv_value(v, decimal_comma) for v in row.values()])
    with (folder / 'cri_samples.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['sample', 'CRI_Ri_CIE1995', 'included_in_Ra'])
        for i in range(1, 15):
            writer.writerow([f'R{i}', csv_value(metrics['cri_Ri'].get(str(i)), decimal_comma), i <= 8])
    (folder / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    lines = [f"Device: {metadata.get('device_id', '')}",
             f"Sample: {metadata.get('sample_name', '')}",
             f"Input unit: {metrics['input_unit']}"]
    for name, value, unit in [('Lux', metrics['lux'], 'lx'),
                              ('PPFD (400-700 nm)', metrics['ppfd_umol_m2_s'], 'umol/m^2/s'),
                              ('ePAR (400-750 nm)', photo['epar_umol_m2_s'], 'umol/m^2/s'),
                              ('xPAR (FR capped at 40% of PAR)', photo['xpar_umol_m2_s'], 'umol/m^2/s'),
                              ('PhR energy (400-700 nm)', photo['phr_W_m2'], 'W/m^2'),
                              ('FR (700-750 nm)', photo['bands']['FR_700_750']['photon_irradiance_umol_m2_s'], 'umol/m^2/s'),
                              ('CRI Ra (CIE 1995)', metrics['cri_Ra'], ''),
                              ('R9', metrics['cri_Ri'].get('9'), ''),
                              ('CCT', metrics['cct_K'], 'K')]:
        lines.append(f'{name}: {value:.6g} {unit}' if value is not None else f'{name}: unavailable')
    lines.append('PAR photon irradiance = PPFD (400-700 nm).')
    for name, entry in photo['ratios'].items():
        value = entry['value']
        lines.append(f'{name}: {value:.6g}' if value is not None else f'{name}: unavailable ({entry["status"]})')
    dli = photo['dli_estimate']
    if dli['photoperiod_hours'] is not None:
        lines.append(f'DLI ESTIMATE assuming constant irradiance for {dli["photoperiod_hours"]:g} hours/day:')
        for name in ['PAR', 'ePAR', 'xPAR']:
            value = dli[name + '_mol_m2_day']
            lines.append(f'  {name}: {value:.6g} mol/m^2/day' if value is not None else f'  {name}: unavailable')
    else:
        lines.append('DLI: not requested; specify daily photoperiod to estimate.')
    unavailable = [name for name, entry in photo['bands'].items() if entry['status'] != 'OK']
    if unavailable:
        lines.append('Bands unavailable (see bands.csv): ' + ', '.join(unavailable))
    lines.append('Quality: ' + ', '.join(metrics['quality_flags']))
    lines.extend('Note: ' + text for text in metrics['warnings'])
    text = '\n'.join(lines) + '\n'
    (folder / 'metrics.txt').write_text(text, encoding='utf-8')
    print(text, flush=True)


def analyse_existing(csv_path, photoperiod_hours=None):
    """Recalculate metrics from a v1.0 or v1.1 export, assuming stated W/m2/nm."""
    path = Path(csv_path).resolve()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter=';'))
    if not rows:
        raise ValueError('Empty spectrum.csv')
    value_column = 'spectral_irradiance_W_m2_nm' if 'spectral_irradiance_W_m2_nm' in rows[0] else 'spectral_value'
    x = [float(row['wavelength_nm'].replace(',', '.')) for row in rows]
    y = [float(row[value_column].replace(',', '.')) for row in rows]
    metadata_path = path.parent / 'measurement.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))['metadata'] if metadata_path.exists() else {}
    mapping_valid = (not metadata or 'end_wavelength_nm' not in metadata or
                     len(x) == metadata['end_wavelength_nm'] - metadata['start_wavelength_nm'] + 1)
    metadata['measurement_timestamp_utc'] = rows[0].get('timestamp_utc', '')
    metrics = calculate_metrics(x, y, wavelength_mapping_valid=mapping_valid, photoperiod_hours=photoperiod_hours)
    metrics['input_unit_source'] = 'User confirmation: exported instrument values are W/m^2/nm.'
    save_metrics(path.parent, metrics, metadata, decimal_comma=metadata.get('csv_decimal', ',') == ',')
    print('Saved metrics alongside:', path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Calculate Lux, CRI, PAR/ePAR/xPAR and spectral bands from spectrum.csv.')
    parser.add_argument('spectrum_csv')
    parser.add_argument('--photoperiod-hours', type=float, help='Optional constant-light daily duration, 0..24 hours; DLI estimate only')
    args = parser.parse_args()
    validate_hours(args.photoperiod_hours)
    analyse_existing(args.spectrum_csv, args.photoperiod_hours)
