import numpy as np

def trova_indice_sincronizzazione(bits):
    """Trova l'indice della prima sequenza di 10 bit a 0."""
    for i in range(len(bits) - 9):
        if all(bit == 0 for bit in bits[i:i + 10]):
            return i  # Restituisce l'indice del primo bit della sequenza
    return -1  # Nessuna sequenza trovata

def decodifica_bit_e_byte(bits, periodo_bit_campioni, indice_partenza=0):
    """Decodifica i bit e i byte, verifica il CRC e decodifica i dati specifici."""

    # Identificazione della sequenza di 10 bit a 0
    sequenza_trovata = False
    indice_primo_bit_successivo = -1
    for i in range(indice_partenza, len(bits) - 9):
        if all(bit == 0 for bit in bits[i:i + 10]):
            sequenza_trovata = True
            indice_primo_bit_successivo = i + 10
            break

    if not sequenza_trovata:
        return None, None, None, None, None, None  # Nessuna sequenza trovata

    # Creazione dell'array di 10 byte
    bytes_decodificati = []
    for i in range(10):
        indice_byte = indice_primo_bit_successivo + i * 9
        if indice_byte + 9 > len(bits):
            return None, None, None, None, None, None  # Indice fuori dai limiti
        if bits[indice_byte] != 1:
            return None, None, None, None, None, indice_byte  # Errore di sincronizzazione
        byte = 0
        for j in range(8):
            byte |= bits[indice_byte + 1 + j] << j
        bytes_decodificati.append(byte)

    # Verifica del CRC-16-CCITT
    if len(bytes_decodificati) >= 2:
        dati = bytes_decodificati[:-2]
        crc_ricevuto = (bytes_decodificati[-1] << 8) | bytes_decodificati[-2]
        crc_calcolato = calc_crc16_ccitt(dati)
        if crc_ricevuto == crc_calcolato:
            return bytes_decodificati, indice_primo_bit_successivo, True, crc_ricevuto, crc_calcolato, None  # CRC OK
        else:
            return bytes_decodificati, indice_primo_bit_successivo, False, crc_ricevuto, crc_calcolato, None  # CRC Errato

    return bytes_decodificati, indice_primo_bit_successivo, None, None, None, None  # Nessun CRC da verificare


def calc_crc16_ccitt(data):
    """Calcola il CRC-16-CCITT."""
    crc = 0x0  # Valore iniziale
    polynomial = 0x1021

    for byte in data:
        b = byte
        for i in range(8):
            bit = ((b >> i) & 1) == 1
            c15 = ((crc >> 15) & 1) == 1
            crc <<= 1
            if c15 ^ bit:
                crc ^= polynomial
        crc &= 0xffff

    # Inversione dell'ordine dei bit del CRC
    crc_reversed = 0
    for i in range(16):
        if (crc >> i) & 1:
            crc_reversed |= 1 << (15 - i)

    return crc_reversed