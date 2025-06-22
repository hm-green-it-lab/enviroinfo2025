import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, List

workDir = "./"
runLocationX86 = "_CPU100\\06-06-202512-59-33"
#runLocationX86 = "-DISABLED_TURBO_CPU100\\06-06-202516-20-40"
runLocationRISC = "_CPU100\\06-06-202512-59-33"
#runLocationRISC = "_CORE-LIMITED-CPU-4\\03-06-202523-12-41"

def calculate_cpu_usage(renaissance_file, procfs_file, benchmark_name, processor, benchmark_start_index=0):
    try:
        # Lese Renaissance Output CSV
        ren_df = pd.read_csv(renaissance_file)

        # Filtere nach dem spezifischen Benchmark und Start-Index
        benchmark_data = ren_df[ren_df['benchmark'] == benchmark_name]
        if benchmark_data.empty:
            raise ValueError(f"Benchmark '{benchmark_name}' nicht in den Daten gefunden!")

        # Stelle sicher, dass der Start-Index gültig ist
        if benchmark_start_index >= len(benchmark_data):
            raise ValueError(f"Start-Index {benchmark_start_index} ist zu groß für Benchmark '{benchmark_name}'")

        # Filtere ab dem gewünschten Start-Index
        benchmark_data = benchmark_data.iloc[benchmark_start_index:]

        # Berechne Start- und Endzeit
        start_time = benchmark_data.iloc[0]['vm_start_unix_ms'] + benchmark_data.iloc[0]['uptime_ns'] / 1_000_000
        end_time = benchmark_data.iloc[-1]['vm_start_unix_ms'] + benchmark_data.iloc[-1]['uptime_ns'] / 1_000_000

        # Lese procfs Ergebnisse
        proc_df = pd.read_csv(procfs_file)

        # Filtere nach /proc/stat Einträgen und Zeitfenster
        proc_df = proc_df[
            (proc_df['SourceFile'].str.match(r'/proc/\d+/stat')) &  # Filtert Einträge wie /proc/11324/stat
            (proc_df['Timestamp'] >= start_time) &
            (proc_df['Timestamp'] <= end_time)
            ]

        # Berechne CPU-Nutzung
        # Setze CPU-Kerne basierend auf Prozessor-Typ
        cpu_cores = 8 if processor == 'RISC-V' else 4

        ticks_per_second = 100

        # Berechne Differenzen zwischen aufeinanderfolgenden Messungen
        proc_df['userTime_diff'] = proc_df['userTime (Ticks)'].diff()
        proc_df['systemTime_diff'] = proc_df['systemTime (Ticks)'].diff()
        proc_df['timestamp_diff'] = proc_df['Timestamp'].diff() / 1000

        # Entferne erste Zeile (NaN durch diff)
        proc_df = proc_df.dropna()

        # Berechne CPU-Auslastung in Prozent
        total_cpu_usage = ((proc_df['userTime_diff'] + proc_df['systemTime_diff']) /
                           (proc_df['timestamp_diff'] * ticks_per_second * cpu_cores)) * 100

        # Füge die CPU-Nutzungswerte dem DataFrame hinzu
        proc_df['cpu_usage'] = total_cpu_usage

        # Berechne relative Sekunden seit Start
        proc_df['relative_seconds'] = np.floor((proc_df['Timestamp'] - proc_df['Timestamp'].iloc[0]) / 1000)

        # Gruppiere die Werte pro Sekunde
        cpu_per_second = proc_df.groupby('relative_seconds')['cpu_usage'].agg(list).reset_index()

        return {
            'benchmark': benchmark_name,
            'start_index': benchmark_start_index,
            'durchschnittliche_cpu_auslastung': total_cpu_usage.mean(),
            'maximale_cpu_auslastung': total_cpu_usage.max(),
            'minimale_cpu_auslastung': total_cpu_usage.min(),
            'start_zeit': start_time,
            'end_zeit': end_time,
            'anzahl_messungen': len(proc_df),
            'cpu_values_per_second': [val for sublist in cpu_per_second['cpu_usage'].tolist() for val in sublist]
        }
    except Exception as e:
        print(f"Fehler bei der Verarbeitung von Benchmark {benchmark_name}: {str(e)}")
        return None


def plot_cpu_usage_boxplots_comparison(alle_ergebnisse: List[Dict]):
    """
    Erstellt Boxplots für jeden Benchmark im Stil des visualizeDurationAsBoxplots-Skripts.
    """
    # Gruppiere Ergebnisse nach Benchmark-Namen
    benchmark_groups = {}
    for ergebnis in alle_ergebnisse:
        if ergebnis is not None:
            benchmark_name = ergebnis['benchmark']
            if benchmark_name not in benchmark_groups:
                benchmark_groups[benchmark_name] = []
            benchmark_groups[benchmark_name].append(ergebnis)

    # Schriftgrößen definieren
    TITLE_SIZE = 20
    LABEL_SIZE = 20
    TICK_SIZE = 16

    # Globale Schriftgröße setzen
    plt.rcParams.update({
        'font.size': TICK_SIZE,
        'axes.titlesize': TITLE_SIZE,
        'axes.labelsize': LABEL_SIZE,
        'xtick.labelsize': TICK_SIZE,
        'ytick.labelsize': TICK_SIZE
    })

    num_benchmarks = len(benchmark_groups)

    # Erstelle Figure mit Subplots
    fig, axes = plt.subplots(1, num_benchmarks, figsize=(20, 6), sharey=True)
    if num_benchmarks == 1:
        axes = [axes]

    # Graustufen-Palette definieren
    palette = sns.color_palette("Greys", n_colors=2)

    # Erstelle für jeden Benchmark einen separaten Plot
    for idx, (benchmark_name, ergebnisse) in enumerate(benchmark_groups.items()):
        # Erstelle DataFrame für den aktuellen Benchmark
        plot_data = []
        processors = []
        for ergebnis in ergebnisse:
            plot_data.extend(ergebnis['cpu_values_per_second'])
            processors.extend([ergebnis['processor']] * len(ergebnis['cpu_values_per_second']))

        df = pd.DataFrame({
            'CPU Utilization (%)': plot_data,
            'Processor': processors
        })

        # Erstelle Boxplot
        sns.boxplot(x='Processor', y='CPU Utilization (%)', data=df,
                    palette=palette, ax=axes[idx])

        # Formatiere Subplot
        axes[idx].set_title(benchmark_name, fontsize=TITLE_SIZE, pad=15)
        axes[idx].set_xlabel('')
        if idx == 0:  # Nur beim ersten Plot y-Label anzeigen
            axes[idx].set_ylabel('CPU Utilization (%)', fontsize=LABEL_SIZE)
        else:
            axes[idx].set_ylabel('')

        # Rotiere x-Achsen-Labels und passe Schriftgröße an
        axes[idx].tick_params(axis='x', rotation=45, labelsize=TICK_SIZE)
        axes[idx].tick_params(axis='y', labelsize=TICK_SIZE)

        # Füge Gitterlinien hinzu
        axes[idx].yaxis.grid(True)

        # Setze y-Achsen-Grenzen
        axes[idx].set_ylim(0, 100)

    # Layout optimieren
    plt.tight_layout(pad=2.0)

    # Boxplot als PDF speichern

    # Boxplot als PDF speichern
    pdf_path = '../X86' + runLocationX86.replace(slash, "_").replace("/", "_") + '_RISC'+ runLocationRISC.replace(slash, "_").replace("/", "_") + '_cpuUtilizationBoxplot.pdf'
    #pdf_path = '../frequencyAndCoreMatchedCpuUtilizationBoxplot.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)

    #pdf_path = 'cpu_usage_boxplots.pdf'
    #   plt.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)

    plt.show()

    print(f"Boxplot wurde erfolgreich als PDF gespeichert: {pdf_path}")

def verarbeite_benchmarks(verzeichnis_configs, benchmark_configs):
    """
    Verarbeitet mehrere Benchmarks aus verschiedenen Verzeichnissen mit Prozessor-Information.
    
    :param verzeichnis_configs: Liste der Verzeichnis-Konfigurationen mit Prozessor-Information
    :param benchmark_configs: Liste von Dictionaries mit Benchmark-Konfigurationen
    """
    alle_ergebnisse = []
    
    for verzeichnis_config in verzeichnis_configs:
        verzeichnis = verzeichnis_config['path']
        processor = verzeichnis_config['processor']
        
        # Generiere Dateinamen basierend auf Prozessor-Typ
        processor_suffix = 'risc' if processor == 'RISC-V' else 'x86'
        renaissance_file = os.path.join(verzeichnis, f'renaissanceOutput_{processor_suffix}.csv')
        procfs_file = os.path.join(verzeichnis, f'procfsResults_{processor_suffix}')
        
        if not (os.path.exists(renaissance_file) and os.path.exists(procfs_file)):
            print(f"Überspringe nicht existierendes Verzeichnis: {verzeichnis}")
            continue
            
        for config in benchmark_configs:
            ergebnis = calculate_cpu_usage(
                renaissance_file,
                procfs_file,
                benchmark_name=config['name'],
                processor=processor,
                benchmark_start_index=config.get('start_index', 0)
            )
            if ergebnis:
                ergebnis['processor'] = processor  # Füge Prozessor-Information hinzu
                alle_ergebnisse.append(ergebnis)
    
    return alle_ergebnisse

# Beispielaufruf
if __name__ == "__main__":
    slash = '\\' if os.name == 'nt' else '/'
    # Definition der Verzeichnis-Konfigurationen mit Prozessor-Information
    verzeichnis_configs = [
        {
            'path': workDir + 'gpl-akka-uct' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-akka-uct' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-fj-kmeans' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-fj-kmeans' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },

        {
            'path': workDir + 'gpl-reactors' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-reactors' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-future-genetic' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-future-genetic' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-mnemonics' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-mnemonics' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-par-mnemonics' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-par-mnemonics' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-rx-scrabble' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-rx-scrabble' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        {
            'path': workDir + 'gpl-scrabble' + runLocationRISC + slash +'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': workDir + 'gpl-scrabble' + runLocationX86 + slash +'X86',
            'processor': 'x86'
        },
        # Weitere Verzeichnisse hier hinzufügen
    ]

    # Definition der Benchmark-Konfigurationen
    benchmark_configs = [
        {'name': 'akka-uct', 'start_index': 24},
        {'name': 'fj-kmeans', 'start_index': 30},
        {'name': 'reactors', 'start_index': 10},
        {'name': 'future-genetic', 'start_index': 50},
        {'name': 'mnemonics', 'start_index': 16},
        {'name': 'par-mnemonics', 'start_index': 16},
        {'name': 'rx-scrabble', 'start_index': 80},
        {'name': 'scrabble', 'start_index': 50},
       # {'name': 'als', 'start_index': 0},
        # Weitere Benchmark-Konfigurationen hier hinzufügen
    ]

    try:
        # Verarbeite alle Benchmarks
        alle_ergebnisse = verarbeite_benchmarks(verzeichnis_configs, benchmark_configs)
        
        # Zeige die Ergebnisse
        for ergebnis in alle_ergebnisse:
            print(f"\nCPU-Auslastungsstatistiken für {ergebnis['benchmark']} ({ergebnis['processor']}):")
            print(f"Durchschnittliche CPU-Auslastung: {ergebnis['durchschnittliche_cpu_auslastung']:.2f}%")
            print(f"Maximale CPU-Auslastung: {ergebnis['maximale_cpu_auslastung']:.2f}%")
            print(f"Minimale CPU-Auslastung: {ergebnis['minimale_cpu_auslastung']:.2f}%")
            print(f"Anzahl der Messungen: {ergebnis['anzahl_messungen']}")
        
        # Erstelle die Boxplots
        plot_cpu_usage_boxplots_comparison(alle_ergebnisse)

    except Exception as e:
        print(f"Fehler: {e}")