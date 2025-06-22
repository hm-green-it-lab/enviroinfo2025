import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

workDir = "./"
runLocationX86 = "_CPU100\\06-06-202512-59-33"
#runLocationX86 = "-DISABLED_TURBO_CPU100\\06-06-202516-20-40"
runLocationRISC = "_CPU100\\06-06-202512-59-33"
#runLocationRISC = "_CORE-LIMITED-CPU-4\\03-06-202523-12-41"

slash = '\\' if os.name == 'nt' else '/'

# Beispiel-Daten für die CSV-Dateien und ihre Dimensionen
csv_files = [
    {'file': workDir + 'gpl-akka-uct' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'akka-uct'},
    {'file': workDir + 'gpl-akka-uct' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'akka-uct'},

    {'file': workDir + 'gpl-fj-kmeans' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'fj-kmeans'},
    {'file': workDir + 'gpl-fj-kmeans' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'fj-kmeans'},

    {'file': workDir + 'gpl-reactors' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'reactors'},
    {'file': workDir + 'gpl-reactors' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'reactors'},

    {'file': workDir + 'gpl-future-genetic' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'future-genetic'},
    {'file': workDir + 'gpl-future-genetic' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'future-genetic'},

    {'file': workDir + 'gpl-mnemonics' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'mnemonics'},
    {'file': workDir + 'gpl-mnemonics' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'mnemonics'},

    {'file': workDir + 'gpl-par-mnemonics' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'par-mnemonics'},
    {'file': workDir + 'gpl-par-mnemonics' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'par-mnemonics'},

    {'file': workDir + 'gpl-rx-scrabble' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'rx-scrabble'},
    {'file': workDir + 'gpl-rx-scrabble' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'rx-scrabble'},

    {'file': workDir + 'gpl-scrabble' + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'scrabble'},
    {'file': workDir + 'gpl-scrabble' + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'scrabble'},
]

# Liste zum Sammeln der Daten
data_list = []

# Dictionary für die zu ignorierenden Zeilen je Run
skip_rows = {
    'akka-uct': 24,      # Beispiel: Ignoriere erste 5 Zeilen
    'fj-kmeans': 30,    # Beispiel: Ignoriere erste 10 Zeilen
    'reactors': 10,      # usw.
    'future-genetic': 50,
    'mnemonics': 16,
    'par-mnemonics': 16,
    'rx-scrabble': 80,
    'scrabble': 50
}


# CSV-Dateien einlesen und Daten vorbereiten
for file_info in csv_files:
    # Bestimme die Anzahl der zu überspringenden Zeilen basierend auf dem Run
    rows_to_skip = skip_rows.get(file_info['run'], 0)  # 0 als Standardwert, falls Run nicht im Dictionary

    # Lies CSV-Datei ein, überspringe die definierten Zeilen
    df = pd.read_csv(file_info['file'],
                     index_col=None,
                     header=0,
                     skiprows=range(1, rows_to_skip + 1))  # +1 weil range exclusive ist
    # 1 als Start, um Header zu behalten

    # Minimalen Timestamp finden
    min_timestamp = df['uptime_ns'].min()

    # Timestamps relativ zum minimalen Timestamp berechnen
    df['uptime_ns'] = df['uptime_ns'] - min_timestamp

    df['duration_s'] = df['duration_ns'] / 1_000_000_000
    # Daten für die erste Minute herausschneiden
    #df = df[df['Relative Timestamp'] >= 60000]

    # Daten für die nächsten 10 Minuten berücksichtigen
    #df = df[df['Relative Timestamp'] <= 660000]

    # Dimensionen hinzufügen
    df['processor'] = file_info['processor']
    df['run'] = file_info['run']

    # Daten zur Liste hinzufügen
    data_list.append(df)

# DataFrame zusammenführen
df = pd.concat(data_list, axis=0, ignore_index=True)

# Daten nach Timestamp gruppieren und die Power-Werte addieren
agg_df = df.groupby(['duration_s', 'processor', 'run']).all().reset_index()

# Reihenfolge der benchmark-Dimensionen definieren
benchmark_order = ['akka-uct', 'fj-kmeans', 'reactors', 'future-genetic', 'mnemonics', 'par-mnemonics', 'rx-scrabble', 'scrabble']

# ... (vorheriger Code bis zur Datenverarbeitung bleibt gleich) ...

# Schriftgrößen definieren
TITLE_SIZE = 20
LABEL_SIZE = 20
TICK_SIZE = 16

# Globale Schriftgröße für matplotlib setzen
plt.rcParams.update({
    'font.size': TICK_SIZE,
    'axes.titlesize': TITLE_SIZE,
    'axes.labelsize': LABEL_SIZE,
    'xtick.labelsize': TICK_SIZE,
    'ytick.labelsize': TICK_SIZE
})

# Anzahl der Benchmarks
n_benchmarks = len(benchmark_order)

# Erstelle Figure mit Subplots
fig, axes = plt.subplots(1, n_benchmarks, figsize=(20, 6), sharey=False)

# Graustufen-Palette definieren
palette = sns.color_palette("Greys", n_colors=2)

# Erstelle für jeden Benchmark einen separaten Plot
for idx, benchmark in enumerate(benchmark_order):
    # Filtere Daten für aktuellen Benchmark
    benchmark_data = df[df['run'] == benchmark]
    
    # Erstelle Boxplot
    sns.boxplot(x='processor', y='duration_s', data=benchmark_data, 
                palette=palette, ax=axes[idx])
    axes[idx].set_ylim(bottom=0)

    # Formatiere Subplot
    axes[idx].set_title(benchmark, fontsize=TITLE_SIZE, pad=15)  # Mehr Abstand zum Plot
    axes[idx].set_xlabel('')
    if idx == 0:  # Nur beim ersten Plot y-Label anzeigen
        axes[idx].set_ylabel('Duration (s)', fontsize=LABEL_SIZE)
    else:
        axes[idx].set_ylabel('')
    
    # Rotiere x-Achsen-Labels und passe Schriftgröße an
    axes[idx].tick_params(axis='x', rotation=45, labelsize=TICK_SIZE)
    axes[idx].tick_params(axis='y', labelsize=TICK_SIZE)
    
    # Füge Gitterlinien hinzu
    axes[idx].yaxis.grid(True)

# Layout optimieren mit mehr Platz für die größeren Beschriftungen
plt.tight_layout(pad=2.0)

# Boxplot als PDF speichern
pdf_path = 'X86' + runLocationX86.replace(slash, "_").replace("/", "_") + '_RISC'+ runLocationRISC.replace(slash, "_").replace("/", "_") + '_durationBoxplot.pdf'
#pdf_path = 'frequencyAndCoreMatchedDurationBoxplot.pdf'
plt.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)

# Boxplot anzeigen
plt.show()

print(f"Boxplot wurde erfolgreich als PDF gespeichert: {pdf_path}")