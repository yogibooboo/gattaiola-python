import numpy as np

def decodifica_bit_e_byte(bits, periodo_bit_campioni):
    """Decodifica i bit e i byte, verifica il CRC e decodifica i dati specifici."""

    # Identificazione della sequenza di 10 bit a 0
    sequenza_trovata = False
    indice_primo_bit_successivo = -1
    for i in range(len(bits) - 9):
        if all(bit == 0 for bit in bits[i:i + 10]):
            sequenza_trovata = True
            indice_primo_bit_successivo = i + 10
            break

    if not sequenza_trovata:
        print("Sequenza di 10 bit a 0 non trovata.")
        return None, None  # Esce dalla funzione se la sequenza non viene trovata

    # Creazione dell'array di 10 byte
    bytes_decodificati = []
    for i in range(10):
        indice_byte = indice_primo_bit_successivo + i * 9
        if indice_byte + 9 > len(bits):
            print("Errore: Indice fuori dai limiti.")
            return None, None  # Esce dalla funzione se l'indice è fuori dai limiti
        if bits[indice_byte] != 1:
            print("Errore di sincronizzazione: Bit di sincronizzazione non trovato.")
            return None, None  # Esce dalla funzione se il bit di sincronizzazione non è 1
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
            print("CRC-16-CCITT OK (bit invertiti)")
        else:
            print("CRC-16-CCITT Errato (bit invertiti)")
            print(f"CRC-16-CCITT Ricevuto: {crc_ricevuto:04X}")
            print(f"CRC-16-CCITT Calcolato: {crc_calcolato:04X}")

    # Decodifica dei dati specifici (codice paese e codice dispositivo)
    country_code_bin = (bytes_decodificati[5] << 2) | (bytes_decodificati[4] >> 6) if len(bytes_decodificati) >= 8 else None
    device_code_bin = (bytes_decodificati[4] & 0x3F) << 32 | (bytes_decodificati[3] << 24) | (bytes_decodificati[2] << 16) | (bytes_decodificati[1] << 8) | bytes_decodificati[0] if len(bytes_decodificati) >= 8 else None

    return bytes_decodificati, indice_primo_bit_successivo, country_code_bin, device_code_bin


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