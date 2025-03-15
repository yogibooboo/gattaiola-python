import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import utility


# Flag per scegliere il tipo di filtro: True per media scorrevole, False per filtro mediano
USA_MEDIA_SCORREVOLE = True  # Imposta a True per usare la media scorrevole, False per il filtro mediano

def media_scorrevole(segnale, larghezza_finestra):
    """Applica una media scorrevole al segnale."""
    finestra = np.ones(larghezza_finestra) / larghezza_finestra
    return np.convolve(segnale, finestra, mode='same')


def esegui_analisi():
    percorso_file = percorso_file_var.get()
    max_campioni_per_bit = int(max_campioni_per_bit_var.get())
    max_bit_totali = int(max_bit_totali_var.get())

    data, header = utility.leggi_file_binario(percorso_file)
    periodo_campionamento = header[7] * 1e6
    durata_bit = 1 / (134.2e3 / 32) * 1e6

    segnale_normalizzato, campioni_per_bit_normalizzato = utility.normalizza_segnale(data, periodo_campionamento, durata_bit, max_campioni_per_bit, max_bit_totali)
    larghezza_finestra = int((durata_bit / 4) / (periodo_campionamento * (int(durata_bit / (periodo_campionamento * max_campioni_per_bit)))))

    if USA_MEDIA_SCORREVOLE:
        segnale_filtrato = media_scorrevole(segnale_normalizzato, larghezza_finestra)
    else:
        segnale_filtrato = utility.filtro_mediano(segnale_normalizzato, larghezza_finestra)

    segnale_filtrato = np.nan_to_num(segnale_filtrato)

    periodo_bit_campioni = campioni_per_bit_normalizzato
    correlazione, picchi = utility.sincronizza_bmc(segnale_filtrato, periodo_bit_campioni)
    segnale_filtrato = np.nan_to_num(segnale_filtrato)

    periodo_bit_campioni = campioni_per_bit_normalizzato
    correlazione, picchi = utility.sincronizza_bmc(segnale_filtrato, periodo_bit_campioni)
    numero_totale_bit = len(segnale_filtrato) // periodo_bit_campioni

    ax1.clear()
    ax1.plot(segnale_normalizzato, label=f'Segnale Normalizzato\nCampioni/bit: {campioni_per_bit_normalizzato}\nBit totali: {len(segnale_normalizzato) // campioni_per_bit_normalizzato}')
    for i in range(0, len(segnale_normalizzato), periodo_bit_campioni):
        ax1.axvline(i, color='black', linestyle='-', linewidth=0.8)
        ax1.axvline(i + periodo_bit_campioni // 2, color='gray', linestyle='--', linewidth=0.5)
    ax1.set_title('Segnale Normalizzato')
    ax1.legend()

    ax2.clear()
    ax2.plot(correlazione, label='Correlazione')
    ax2.plot(picchi, correlazione[picchi], "x", label='Picchi')
    for i in range(0, len(segnale_filtrato), periodo_bit_campioni):
        ax2.axvline(i, color='black', linestyle='-', linewidth=0.8)
        ax2.axvline(i + periodo_bit_campioni // 2, color='gray', linestyle='--', linewidth=0.5)
    ax2.set_title('Correlazione e Picchi')
    ax2.legend()

    fig.canvas.draw_idle()



    # Decodifica dei picchi e identificazione del tipo di picco
    distanze = np.diff(picchi)
    soglia_mezzo_bit = periodo_bit_campioni * 3 // 4
    bits = []
    tipi_picchi = []  # Array per memorizzare il tipo di picco
    i = 0
    while i < len(distanze):
        if distanze[i] < soglia_mezzo_bit:
            if i + 1 < len(distanze) and distanze[i + 1] < soglia_mezzo_bit:
                bits.append(0)
                tipi_picchi.append(0)  # Inizio bit 0
                tipi_picchi.append(2)  # Secondo picco bit 0
                i += 2
            else:
                i += 1  # Salta il mezzo bit singolo
                tipi_picchi.append(3)  # bit scartato
        else:
            bits.append(1)
            tipi_picchi.append(1)  # Inizio bit 1
            i += 1

    print("Sequenza di bit decodificata:", bits)

    # Visualizzazione dei picchi con il tipo di picco accanto
    for i, picco in enumerate(picchi):
        if i < len(tipi_picchi):
            tipo_picco = tipi_picchi[i]
            colore = 'black'
            if tipo_picco == 1:
                colore = 'blue'
            elif tipo_picco == 2:
                colore = 'yellow'
            elif tipo_picco == 3:
                colore = 'red'
            ax2.text(picco, correlazione[picco], str(tipo_picco), verticalalignment='center', horizontalalignment='center', fontsize=12, fontweight='bold', color=colore)

    # Visualizzazione dei bit e delle posizioni dei bit
    posizioni_bit = np.arange(len(bits)) * periodo_bit_campioni
    for i, bit in enumerate(bits):
        ax2.text(posizioni_bit[i], 2, str(bit), verticalalignment='center', horizontalalignment='center')
        ax2.text(posizioni_bit[i], -2, str(i), verticalalignment='center', horizontalalignment='center')


    # Identificazione della sequenza di 10 bit a 0
    sequenza_trovata = False
    indice_primo_bit_successivo = -1
    for i in range(len(bits) - 9):
        if all(bit == 0 for bit in bits[i:i + 10]):
            sequenza_trovata = True
            indice_primo_bit_successivo = i + 10
            break

    # Visualizza l'indice sul grafico
    if indice_primo_bit_successivo != -1:

                ax2.axvline(posizioni_bit[indice_primo_bit_successivo], color='blue', linestyle='--', linewidth=2)

    ax2.set_title('Correlazione, Picchi e Bit Decodificati')
    ax2.legend()

    fig.canvas.draw_idle()

    if sequenza_trovata:
        print("Sequenza di 10 bit a 0 trovata. Indice del primo bit successivo:", indice_primo_bit_successivo)
    else:
        print("Sequenza di 10 bit a 0 non trovata.")
        return  # Esce dalla funzione se la sequenza non viene trovata

    # Creazione dell'array di 10 byte
    bytes_decodificati = []
    for i in range(10):
        indice_byte = indice_primo_bit_successivo + i * 9
        if indice_byte + 9 > len(bits):
            print("Errore: Indice fuori dai limiti.")
            return  # Esce dalla funzione se l'indice è fuori dai limiti
        if bits[indice_byte] != 1:
            print("Errore di sincronizzazione: Bit di sincronizzazione non trovato.")
            return  # Esce dalla funzione se il bit di sincronizzazione non è 1
        byte = 0
        for j in range(8):
            byte |= bits[indice_byte + 1 + j] << j
        bytes_decodificati.append(byte)

    # Stampa dei byte in binario
    print("Byte decodificati:")
    for byte in bytes_decodificati:
        print(f"{byte:08b}")

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

    # Visualizzazione dei dati

    if len(bytes_decodificati) >= 8:
        # Country code
        country_code_bin = (bytes_decodificati[5] << 2) | (bytes_decodificati[4] >> 6)
        print(f"Country Code: {country_code_bin}")

        # Codice dispositivo
        device_code_bin = (bytes_decodificati[4] & 0x3F) << 32 | (bytes_decodificati[3] << 24) | (bytes_decodificati[2] << 16) | (bytes_decodificati[1] << 8) | (bytes_decodificati[0])
        print(f"Device Code: {device_code_bin}")

    # Visualizzazione dei bit sul secondo grafico

    #posizioni_bit = np.arange(len(bits)) * periodo_bit_campioni
    #for i, bit in enumerate(bits):
    #    ax2.text(posizioni_bit[i], 0, str(bit), verticalalignment='center', horizontalalignment='center')

    # Visualizza l'indice sul grafico
    if indice_primo_bit_successivo != -1:
        ax2.axvline(posizioni_bit[indice_primo_bit_successivo], color='blue', linestyle='--', linewidth=2)

    ax2.set_title('Correlazione, Picchi e Bit Decodificati')
    ax2.legend()

    fig.canvas.draw_idle()

    config['max_campioni_per_bit'] = max_campioni_per_bit
    config['max_bit_totali'] = max_bit_totali
    config['percorso_file'] = percorso_file
    utility.salva_configurazione(config)

def seleziona_file():
    percorso_file = filedialog.askopenfilename(filetypes=[("File BIN", "*.bin")])
    percorso_file_var.set(percorso_file)

def sincronizza_assi(event):
    if event.inaxes == ax1:
        ax2.set_xlim(ax1.get_xlim())
    elif event.inaxes == ax2:
        ax1.set_xlim(ax2.get_xlim())
    fig.canvas.draw_idle()

def calc_crc16_ccitt(data):
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

config = utility.leggi_configurazione()

window = tk.Tk()
window.title("Analisi Segnale")

percorso_file_var = tk.StringVar(value=config['percorso_file'])
max_campioni_per_bit_var = tk.StringVar(value=str(config['max_campioni_per_bit']))
max_bit_totali_var = tk.StringVar(value=str(config['max_bit_totali']))

tk.Label(window, text="File:").grid(row=0, column=0)
tk.Entry(window, textvariable=percorso_file_var, width=50).grid(row=0, column=1)
tk.Button(window, text="Scegli File", command=seleziona_file).grid(row=0, column=2)

tk.Label(window, text="Max Campioni/bit:").grid(row=1, column=0)
tk.Entry(window, textvariable=max_campioni_per_bit_var).grid(row=1, column=1)

tk.Label(window, text="Max Bit Totali:").grid(row=2, column=0)
tk.Entry(window, textvariable=max_bit_totali_var).grid(row=2, column=1)

tk.Button(window, text="Esegui", command=esegui_analisi).grid(row=3, column=1)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))
plt.tight_layout()


# Sposta la finestra dei grafici più in alto
manager = plt.get_current_fig_manager()
screen_height = manager.window.winfo_screenheight()
current_x = manager.window.winfo_x()
current_y = manager.window.winfo_y()
new_y = current_y + int(0.03 * screen_height)
manager.window.geometry(f"+{current_x}+{new_y}")



plt.show(block=False)

fig.canvas.mpl_connect('motion_notify_event', sincronizza_assi)

window.mainloop()