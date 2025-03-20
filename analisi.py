import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import utility
import utility2
import os
import struct
import asyncio
import websockets
from pathlib import Path

# Flag per scegliere il tipo di filtro: True per media scorrevole, False per filtro mediano
USA_MEDIA_SCORREVOLE = True  # Imposta a True per usare la media scorrevole, False per il filtro mediano
DEBUG_CONTINUA_DOPO_SUCCESSO = False #aggiunta qui

def media_scorrevole(segnale, larghezza_finestra):
    """Applica una media scorrevole al segnale."""
    finestra = np.ones(larghezza_finestra) / larghezza_finestra
    return np.convolve(segnale, finestra, mode='same')

async def acquisisci_da_esp32():
    """Acquisisce i dati dall'ESP32 tramite WebSocket."""
    uri = "ws://192.168.1.25/ws"  # Sostituisci con l'URI del tuo ESP32
    try:
        status_label.config(text="Stato: Connessione in corso...")
        async with websockets.connect(uri) as websocket:
            status_label.config(text="Stato: Connesso")
            await websocket.send("get_buffer")
            status_label.config(text="Stato: Download in corso...")
            blob = await websocket.recv()
            download_path = str(Path.home() / "Downloads" / "adc_buffer.bin")
            with open(download_path, "wb") as f:
                f.write(blob)
            percorso_file_var.set(download_path)  # Aggiorna il percorso del file nella GUI
            status_label.config(text="Stato: Buffer ricevuto e salvato")
    except Exception as e:
        status_label.config(text=f"Errore: {e}")

def avvia_acquisizione():
    """Avvia l'acquisizione asincrona."""
    asyncio.run(acquisisci_da_esp32())


def esegui_analisi():
    percorso_file = percorso_file_var.get()
    max_campioni_per_bit = int(max_campioni_per_bit_var.get())
    max_bit_totali = int(max_bit_totali_var.get())

    nome_file = os.path.basename(percorso_file)

    if nome_file.lower().startswith("adc_"):
        # Gestione file "adc_"
        with open(percorso_file, "rb") as f:
            data = f.read()
        segnale_normalizzato = np.array(struct.unpack("<" + "h" * (len(data) // 2), data))
        periodo_campionamento = 1 / 134.2e3 * 1e6 #periodo in microsecondi
        durata_bit = 1 / (134.2e3 / 32) * 1e6
        campioni_per_bit_normalizzato = int(durata_bit / periodo_campionamento)
    else:
        # Gestione file normali
        data, header = utility.leggi_file_binario(percorso_file)
        periodo_campionamento = header[7] * 1e6
        durata_bit = 1 / (134.2e3 / 32) * 1e6

        segnale_normalizzato, campioni_per_bit_normalizzato = utility.normalizza_segnale(data, periodo_campionamento, durata_bit, max_campioni_per_bit, max_bit_totali)
    larghezza_finestra = int((durata_bit / 4) / periodo_campionamento)
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
            tipi_picchi.append(1)  #
            i += 1  # Inizio bit 1

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

    # Trova l'indice di sincronizzazione iniziale
    indice_partenza = utility2.trova_indice_sincronizzazione(bits)
    if indice_partenza == -1:
        print("Nessuna sequenza di sincronizzazione trovata.")
        return

    sequenze_trovate = 0
    while indice_partenza <= len(bits) - 10:
        sequenze_trovate += 1
        risultati = utility2.decodifica_bit_e_byte(bits, periodo_bit_campioni, indice_partenza)

        if risultati:
            bytes_decodificati, indice_primo_bit_successivo, crc_ok, crc_ricevuto, crc_calcolato, errore_sincronizzazione = risultati
            print(f"\nCiclo {sequenze_trovate}: Ricerca da indice {indice_partenza}") 

            if errore_sincronizzazione is not None:
                print(f"Errore di sincronizzazione all'indice {errore_sincronizzazione}")
                indice_partenza = errore_sincronizzazione + 1
                continue

            # Stampa dei byte in binario
            print("Byte decodificati:")
            if bytes_decodificati is not None: #aggiunta qui
                for byte in bytes_decodificati:
                    print(f"{byte:08b}")
            else:
                print("Errore nella decodifica dei byte.") #aggiunta qui

            if crc_ok is None: # nessun crc da verificare
                print("Nessun CRC da verificare.")
            elif crc_ok:
                print("Decodifica riuscita!")
                print(f"CRC Ricevuto: {crc_ricevuto:04X}") #aggiunta visualizzazione
                if crc_calcolato is not None: #aggiunto controllo
                    print(f"CRC Calcolato: {crc_calcolato:04X}") #aggiunta visualizzazione
                if not DEBUG_CONTINUA_DOPO_SUCCESSO: #modifica qui
                    break
            else:
                print("CRC Errato.")
                print(f"CRC Ricevuto: {crc_ricevuto:04X}")
                if crc_calcolato is not None: #aggiunto controllo
                    print(f"CRC Calcolato: {crc_calcolato:04X}") #aggiunta visualizzazione

            if indice_primo_bit_successivo is not None: #aggiunta qui
                indice_partenza = indice_primo_bit_successivo + 1
            else:
                indice_partenza = indice_partenza + 10 #aggiunta qui
        else:
            print(f"\nCiclo {sequenze_trovate}: Errore di sincronizzazione da indice {indice_partenza}") #modifica qui
            break

        print(f"Fine ciclo {sequenze_trovate}: Prossima ricerca da indice {indice_partenza}")







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

# Aggiunta del pulsante "Acquisisci da ESP32"
pulsante_esp32 = tk.Button(window, text="Acquisisci da ESP32", command=avvia_acquisizione)
pulsante_esp32.grid(row=4, column=1)

# Aggiunta della label per lo stato della connessione
status_label = tk.Label(window, text="Stato: Inattivo")
status_label.grid(row=5, column=1)


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