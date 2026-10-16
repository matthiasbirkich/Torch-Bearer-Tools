#!/usr/bin/env python3
"""Local full-spectrum export using the ZoidTechnology Torch Bearer protocol.

SPDX-License-Identifier: GPL-3.0-or-later
No network calls. Run next to the upstream protocol.py.
"""
import argparse
from collections import deque
import csv
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import time

from protocol import MessageType, ExposureStatus, build_message, calculate_checksum, parse_message

VERSION = '1.2.2'
SOURCE = 'https://github.com/ZoidTechnology/Torch-Bearer-Tools'


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def jsonable(value):
    if isinstance(value, Enum):
        return {'name': value.name, 'code': value.value}
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def number(value, decimal_comma=False):
    if isinstance(value, float):
        result = repr(value)  # round-trip precision; no deliberate rounding
        return result.replace('.', ',') if decimal_comma else result
    return value


def write_spectrum(path, message, metadata, observation_no, decimal_comma):
    """Export every decoded bin, without cropping to the visible range."""
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle, delimiter=';')
        writer.writerow(['observation_no', 'timestamp_utc', 'device_id', 'point_index',
                         'wavelength_nm', 'spectral_irradiance_W_m2_nm', 'encoded_uint16',
                         'exposure_time_ms', 'exposure_status'])
        for index, value in enumerate(message['spectrum']):
            writer.writerow([observation_no, message['timestamp_utc'], metadata.get('device_id', ''),
                             index, metadata['start_wavelength_nm'] + index,
                             number(value, decimal_comma), message['encoded_spectrum'][index],
                             number(message['exposure_time'], decimal_comma),
                             message['exposure_status'].name])


class Capture:
    """Queue complete frames; preserve raw traffic, including undecodable bytes."""
    def __init__(self, port, folder):
        self.port = port
        self.buffer = b''
        self.pending = deque()
        self.rx_file = (folder / 'received.bin').open('wb')
        self.tx_file = (folder / 'sent.bin').open('wb')
        self.journal = (folder / 'messages.jsonl').open('w', encoding='utf-8')
        self.messages = []

    def log(self, event):
        self.journal.write(json.dumps(jsonable(event), ensure_ascii=False, allow_nan=False) + '\n')
        self.journal.flush()

    def send(self, kind, data=b''):
        frame = build_message(kind, data)
        self.port.write(frame)
        self.tx_file.write(frame)
        self.tx_file.flush()
        self.log({'direction': 'tx', 'timestamp_utc': utc_now(),
                  'message_type': kind, 'frame_hex': frame.hex()})

    def receive(self, deadline):
        while not self.pending:
            if time.monotonic() >= deadline:
                raise TimeoutError('No complete reply before the timeout.')
            chunk = self.port.read(max(1, self.port.in_waiting))
            if not chunk:
                continue
            self.rx_file.write(chunk)
            self.rx_file.flush()
            self.buffer += chunk
            while len(self.buffer) >= 5:
                if not self.buffer.startswith(b'\xcc\x81'):
                    raise ValueError('Unexpected frame start; received bytes saved in received.bin.')
                length = int.from_bytes(self.buffer[2:5], 'little')
                if not 9 <= length <= 1048576:
                    raise ValueError(f'Invalid frame length: {length}')
                if len(self.buffer) < length:
                    break
                frame, self.buffer = self.buffer[:length], self.buffer[length:]
                record = {'direction': 'rx', 'timestamp_utc': utc_now(),
                          'frame_hex': frame.hex(), 'message_type_code': frame[5]}
                try:
                    if frame[-2:] != b'\r\n' or calculate_checksum(frame[:-3]) != frame[-3]:
                        raise ValueError('Invalid checksum or frame ending')
                    kind = MessageType(frame[5])
                    payload = frame[6:-3]
                    decoded = parse_message(kind, payload)
                    if kind == MessageType.GET_DATA:
                        if len(payload) < 19 or (len(payload) - 19) % 2:
                            raise ValueError('Invalid spectral payload size')
                        status, exposure_us, exponent, sn, ex_info = struct.unpack_from('<BIHIQ', payload)
                        decoded.update({'encoded_spectrum': [v[0] for v in struct.iter_unpack('<H', payload[19:])],
                                        'exposure_time_us': exposure_us, 'encoded_exponent': exponent,
                                        'sn': sn, 'ex_info': ex_info, 'status_code': status})
                    decoded['timestamp_utc'] = record['timestamp_utc']
                    record['decoded'] = jsonable(decoded)
                    self.pending.append(decoded)
                except Exception as error:
                    record['decode_error'] = str(error)
                    self.messages.append(record)
                    self.log(record)
                    raise
                self.messages.append(record)
                self.log(record)
        return self.pending.popleft()

    def expected(self, kind, seconds=10):
        deadline = time.monotonic() + seconds
        while True:
            message = self.receive(deadline)
            if message['message_type'] == kind:
                return message
            print('Additional reply:', message['message_type'].name, flush=True)

    def close(self):
        self.rx_file.close()
        self.tx_file.close()
        self.journal.close()


def fill_spectral_colours(axes, wavelength_nm, irradiance):
    """Approximate visible wavelength colours clipped to the area under the curve.

    Colour is illustrative only, including false colours for UV/NIR. No values change.
    """
    import numpy as np
    from matplotlib.patches import Polygon

    x = np.asarray(wavelength_nm, dtype=float)
    y = np.asarray(irradiance, dtype=float)
    if len(x) < 2:
        return
    low = min(0., float(np.min(y)))
    high = max(0., float(np.max(y)))
    if low == high:
        return
    # A single raster avoids seams between separate coloured polygons.
    grid = np.linspace(x[0], x[-1], 4097)
    centres = (grid[:-1] + grid[1:]) / 2
    colours = np.empty((len(centres), 3))
    uv = centres < 380
    visible = (centres >= 380) & (centres <= 780)
    nir = centres > 780
    # Illustrative RGB anchor colours; independent of colour-science APIs.
    anchors_nm = np.array([380., 440., 490., 510., 580., 645., 780.])
    anchors_rgb = np.array([[.6, 0, 1], [0, 0, 1], [0, 1, 1],
                            [0, 1, 0], [1, 1, 0], [1, 0, 0], [1, 0, 0]])
    for channel in range(3):
        colours[visible, channel] = np.interp(centres[visible], anchors_nm, anchors_rgb[:, channel])
        # UV and NIR are false colours, not human-visible spectral colours.
        colours[uv, channel] = np.interp(centres[uv], [340., 380.],
                                        [[.22, .06, .36][channel], anchors_rgb[0, channel]])
        colours[nir, channel] = np.interp(centres[nir], [780., 1000.],
                                         [anchors_rgb[-1, channel], [.30, .045, .065][channel]])
    image = axes.imshow(colours[np.newaxis, :, :],
                        extent=(float(x[0]), float(x[-1]), low, high),
                        origin='lower', aspect='auto', interpolation='nearest',
                        alpha=.85, zorder=1)
    vertices = np.vstack(([x[0], 0], np.column_stack((x, y)), [x[-1], 0]))
    clip = Polygon(vertices, closed=True, transform=axes.transData)
    image.set_clip_path(clip)
    image.sticky_edges.x.clear()
    image.sticky_edges.y.clear()



def plot_spectrum(folder, message, metadata, show=False):
    import matplotlib
    if not show:
        matplotlib.use('Agg')  # PNG export works without Tcl/Tk
    else:
        import glob
        for variable, pattern in [('TCL_LIBRARY', 'tcl/tcl*/init.tcl'), ('TK_LIBRARY', 'tcl/tk*/tk.tcl')]:
            matches = glob.glob(str(Path(sys.base_prefix) / pattern))
            if matches:
                os.environ[variable] = str(Path(matches[0]).parent)
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator
    x = [metadata['start_wavelength_nm'] + i for i in range(len(message['spectrum']))]
    fig, axes = plt.subplots(figsize=(10, 5), layout='constrained')
    fill_spectral_colours(axes, x, message['spectrum'])
    axes.plot(x, message['spectrum'], color='#202020', linewidth=1.4, zorder=3)
    title = f"{metadata.get('device_id', '')} | {message['exposure_time']} ms"
    metrics = metadata.get('metrics', {})
    if metrics:
        def display(key):
            value = metrics.get(key)
            return f'{value:.3f}' if value is not None else 'n/a'
        title += (f"\nLux: {display('lux')} lx | PPFD: {display('ppfd_umol_m2_s')} µmol/m²/s"
                  f" | CRI Ra: {display('cri_Ra')}")
    axes.set(xlabel='Wellenlänge λ (nm)',
             ylabel='Spektrale Bestrahlungsstärke (W·m⁻²·nm⁻¹)', title=title)
    if len(x) > 1:
        axes.set_xlim(x[0], x[-1])
    axes.xaxis.set_major_locator(MultipleLocator(100))
    axes.xaxis.set_minor_locator(MultipleLocator(10))
    axes.tick_params(axis='x', which='major', length=6)
    axes.tick_params(axis='x', which='minor', length=3)
    axes.set_axisbelow(True)
    axes.grid(axis='y', which='major', alpha=.22)
    # Only 50-nm grid lines, while keeping 10-nm tick marks uncluttered.
    for wavelength in range(50 * (int(x[0]) // 50 + 1), int(x[-1]) + 1, 50):
        axes.axvline(wavelength, color='#888888', alpha=.22,
                     linewidth=.7, zorder=0)
    for boundary in (380, 780):
        if x[0] < boundary < x[-1]:
            axes.axvline(boundary, color='#777777', linestyle=':',
                         linewidth=.8, alpha=.55, zorder=2)
    for left, right, label in ((x[0], min(380, x[-1]), 'UV'),
                               (max(380, x[0]), min(780, x[-1]), 'sichtbarer Bereich'),
                               (max(780, x[0]), x[-1], 'NIR')):
        if right - left >= 25:
            axes.text((left + right) / 2, .97, label,
                      transform=axes.get_xaxis_transform(), ha='center', va='top',
                      fontsize=9, color='#444444')
    fig.supxlabel('Farbunterlegung schematisch; UV und Infrarot sind für das menschliche Auge unsichtbar.',
                  fontsize=8, color='#555555')
    fig.savefig(folder / 'spectrum.png', dpi=180)
    if show:
        plt.show()
    plt.close(fig)


def acquire(args, serial_factory=None):
    if serial_factory is None:
        from serial import Serial
        serial_factory = Serial
    parent = Path(args.output).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    label = re.sub(r'[^A-Za-z0-9_-]+', '_', args.name).strip('_') or 'measurement'
    folder = parent / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_' + label)
    folder.mkdir()  # new directory per run; never overwrite another measurement
    metadata = {'exporter_version': VERSION, 'protocol_source': SOURCE,
                'started_utc': utc_now(), 'port': args.port, 'baudrate': 115200,
                'sample_name': args.name, 'python_version': platform.python_version(),
                'status': 'started', 'warnings': [],
                'spectral_value_unit': 'W/m^2/nm',
                'spectral_value_unit_source': 'Confirmed by user for this device.',
                'wavelength_mapping': 'start_wavelength + point_index; 1 nm per bin, matching upstream main.py.',
                'csv_separator': ';', 'csv_decimal': ',' if args.decimal_comma else '.',
                'normalization_applied': False, 'selected_observation_no': None}
    capture = None
    selected = None
    observation_no = 0
    stop_sent = False
    code = 0
    print('Output directory:', folder, flush=True)
    try:
        with serial_factory(args.port, 115200, timeout=0.1, write_timeout=5) as port:
            capture = Capture(port, folder)
            try:
                capture.send(MessageType.GET_DEVICE_ID, b'\x18')
                metadata['device_id'] = capture.expected(MessageType.GET_DEVICE_ID)['device_id']
                print('Device ID:', metadata['device_id'], flush=True)
                capture.send(MessageType.GET_RANGE)
                reply = capture.expected(MessageType.GET_RANGE)
                metadata['start_wavelength_nm'] = reply['start_wavelength']
                metadata['end_wavelength_nm'] = reply['end_wavelength']
                print('Range:', reply['start_wavelength'], '-', reply['end_wavelength'], 'nm', flush=True)
                capture.send(MessageType.GET_EXPOSURE_MODE)
                metadata['exposure_mode'] = capture.expected(MessageType.GET_EXPOSURE_MODE)['exposure_mode'].name
                capture.send(MessageType.GET_DATA)
                deadline = time.monotonic() + args.timeout
                while True:
                    reply = capture.receive(deadline)
                    if reply['message_type'] != MessageType.GET_DATA:
                        continue
                    observation_no += 1
                    write_spectrum(folder / f'observation_{observation_no:04d}.csv', reply, metadata,
                                   observation_no, args.decimal_comma)
                    print(f"Observation {observation_no}: {reply['exposure_status'].name}, "
                          f"{reply['exposure_time']} ms, {len(reply['spectrum'])} points", flush=True)
                    expected_count = metadata['end_wavelength_nm'] - metadata['start_wavelength_nm'] + 1
                    if len(reply['spectrum']) != expected_count:
                        warning = (f"Range implies {expected_count} bins at 1 nm, but received "
                                   f"{len(reply['spectrum'])}. All bins retained; wavelength mapping needs verification.")
                        if warning not in metadata['warnings']:
                            metadata['warnings'].append(warning)
                    if reply['exposure_status'] == ExposureStatus.NORMAL:
                        selected = reply
                        metadata['selected_observation_no'] = observation_no
                        write_spectrum(folder / 'spectrum.csv', selected, metadata, observation_no, args.decimal_comma)
                        metadata['point_count'] = len(selected['spectrum'])
                        metadata['exposure_time_ms'] = selected['exposure_time']
                        metadata['exposure_status'] = selected['exposure_status'].name
                        metadata['measurement_timestamp_utc'] = selected['timestamp_utc']
                        break
                capture.send(MessageType.STOP)
                stop_sent = True
                try:
                    capture.expected(MessageType.STOP, seconds=3)
                    metadata['stop_acknowledged'] = True
                except TimeoutError:
                    metadata['stop_acknowledged'] = False
                    metadata['warnings'].append('STOP acknowledgement missing; measurement data saved.')
                metadata['status'] = 'complete'
            finally:
                if not stop_sent:
                    try:
                        capture.send(MessageType.STOP)
                    except Exception:
                        pass
    except KeyboardInterrupt:
        metadata.update(status='interrupted', error='Interrupted by user')
        code = 130
    except Exception as error:
        metadata.update(status='error', error=f'{type(error).__name__}: {error}')
        code = 1
    finally:
        metadata['finished_utc'] = utc_now()
        metadata['observations_exported'] = observation_no
        messages = capture.messages if capture else []
        if capture:
            metadata['unparsed_tail_hex'] = capture.buffer.hex()
            capture.close()
        (folder / 'measurement.json').write_text(json.dumps({'metadata': metadata, 'received_messages': messages},
                                                          ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    if selected:
        try:
            from spectral_metrics import calculate_metrics, save_metrics
            x = [metadata['start_wavelength_nm'] + i for i in range(len(selected['spectrum']))]
            expected_count = metadata['end_wavelength_nm'] - metadata['start_wavelength_nm'] + 1
            metrics = calculate_metrics(x, selected['spectrum'], len(x) == expected_count,
                                        photoperiod_hours=getattr(args, 'photoperiod_hours', None))
            save_metrics(folder, metrics, metadata, args.decimal_comma)
            metadata['metrics'] = metrics
        except Exception as error:
            metadata['warnings'].append(f'Metrics failed, numerical spectrum preserved: {error}')
            metadata['metrics_error'] = f'{type(error).__name__}: {error}'
        (folder / 'measurement.json').write_text(json.dumps({'metadata': metadata, 'received_messages': capture.messages},
                                                           ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    if selected and not args.no_plot:
        try:
            plot_spectrum(folder, selected, metadata, args.show)
        except Exception as error:
            metadata['warnings'].append(f'Plot failed, numerical data preserved: {error}')
            document = {'metadata': metadata, 'received_messages': capture.messages}
            (folder / 'measurement.json').write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    if metadata.get('error'):
        print('ERROR:', metadata['error'], flush=True)
    for warning in metadata['warnings']:
        print('NOTE:', warning, flush=True)
    print('Saved:', folder, flush=True)
    return code, folder


def main():
    parser = argparse.ArgumentParser(description='Export all received Torch Bearer spectral bins and raw USB serial traffic.')
    parser.add_argument('port', help='Serial port, e.g. COM4')
    parser.add_argument('--output', default=str(Path(__file__).resolve().parent / 'Messungen'))
    parser.add_argument('--name', default='measurement', help='Optional sample label')
    parser.add_argument('--timeout', type=float, default=60, help='Maximum seconds to await normal exposure')
    parser.add_argument('--decimal-dot', dest='decimal_comma', action='store_false', help='CSV with decimal dot instead of German decimal comma')
    parser.add_argument('--no-plot', action='store_true', help='Export data only; no Matplotlib needed')
    parser.add_argument('--photoperiod-hours', type=float, help='Optional 0..24 hours/day for a constant-light DLI estimate')
    parser.add_argument('--show', action='store_true', help='Also open the plot window (auto-detect Tcl/Tk paths)')
    args = parser.parse_args()
    from photobiology_metrics import validate_hours
    try:
        validate_hours(args.photoperiod_hours)
    except ValueError as error:
        parser.error(str(error))
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    print('Spektralfarben aktiv (v1.2.2: UV/NIR, Teilstriche 10 nm)', flush=True)
    print('Skript:', Path(__file__).resolve(), flush=True)
    return acquire(args)[0]


if __name__ == '__main__':
    sys.exit(main())
