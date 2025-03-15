import struct
import numpy as np
from scipy.signal import find_peaks
import math
import os

def leggi_file_binario(percorso_file):
    with open(percorso_file, 'rb') as f:
        file_header = struct.unpack('<2sHIQ', f.read(16))
        waveform_header = struct.unpack('IIIIIfdddII16s16s24s16s', f.read(128))
        waveform_data_header = struct.unpack('<IHHQ', f.read(16))
        data = np.fromfile(f, dtype=np.float32, count=1000000)
    return data, waveform_header

def normalizza_segnale(segnale, periodo_campionamento, durata_bit, max_campioni_per_bit, max_bit_totali):
    campioni_per_bit_originale = int(durata_bit / periodo_campionamento)
    if campioni_per_bit_originale <= max_campioni_per_bit:
        m = 1
    else:
        m = int(math.ceil(campioni_per_bit_originale / max_campioni_per_bit))

    segnale_normalizzato = segnale[::m]
    campioni_per_bit_normalizzato = int(durata_bit / (periodo_campionamento * m))

    lunghezza_segnale_normalizzato = max_bit_totali * campioni_per_bit_normalizzato
    if len(segnale_normalizzato) > lunghezza_segnale_normalizzato:
        segnale_normalizzato = segnale_normalizzato[:lunghezza_segnale_normalizzato]

    return segnale_normalizzato, campioni_per_bit_normalizzato

def filtro_mediano(segnale, dimensione_finestra):
    padding = dimensione_finestra // 2
    segnale_padded = np.pad(segnale, padding, mode='edge')
    segnale_filtrato = np.array([np.median(segnale_padded[i:i+dimensione_finestra]) for i in range(len(segnale))])
    return segnale_filtrato

def sincronizza_bmc(segnale, periodo_bit):
    forma_onda_ideale = np.concatenate([np.ones(periodo_bit // 2), -np.ones(periodo_bit // 2)])
    correlazione = np.correlate(segnale, forma_onda_ideale, mode='same')
    picchi, _ = find_peaks(np.abs(correlazione), prominence=0.5)
    return correlazione, picchi

def leggi_configurazione():
    config = {}
    if os.path.exists('config.txt'):
        with open('config.txt', 'r') as f:
            for line in f:
                key, value = line.strip().split('=')
                config[key] = value
                if key != 'percorso_file':
                    config[key] = int(value)
    else:
        config['max_campioni_per_bit'] = 100
        config['max_bit_totali'] = 100
        config['percorso_file'] = ''
    return config

def salva_configurazione(config):
    with open('config.txt', 'w') as f:
        for key, value in config.items():
            f.write(f'{key}={value}\n')