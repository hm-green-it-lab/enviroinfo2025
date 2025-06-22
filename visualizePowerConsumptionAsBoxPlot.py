import os
import pandas as pd
import matplotlib.pyplot as plt

workDir = "./"
runLocationX86 = "baseline-measurement_shelly-only\\05-06-202523-33-39"
runLocationX86InclMeasurements = "baseline-measurement\\05-06-202511-18-36"
runLocationRISC = "baseline-measurement_shelly-only\\05-06-202523-33-39"
runLocationRISCInclMeasurements = "baseline-measurement\\05-06-202511-18-36"
slash = '\\' if os.name == 'nt' else '/'

# Definition der einzulesenden Dateipaare
data_sources = [
    {
        'power_file': workDir + runLocationX86 + f'{slash}X86{slash}shellyReaderResults_x86',
        'rapl_file': None,  # kein RAPL in diesem Fall
        'benchmark_file': workDir + runLocationX86 + f'{slash}X86{slash}renaissanceOutput_x86.csv',
        'processor': 'X86',
        'benchmark': 'Idle',
        'color': '0.2'
    },
    {
        'power_file': workDir + runLocationX86InclMeasurements + f'{slash}X86{slash}shellyReaderResults_x86',
        'rapl_file': workDir + runLocationX86InclMeasurements + f'{slash}X86{slash}raplResults_x86',
        'benchmark_file': workDir + runLocationX86InclMeasurements + f'{slash}X86{slash}renaissanceOutput_x86.csv',
        'processor': 'X86',
        'benchmark': 'ProcFS and RAPL \nMeasurements',
        'color': '0.4'
    },
    {
        'power_file': workDir + runLocationRISC + f'{slash}RISC{slash}shellyReaderResults_risc',
        'rapl_file': None,
        'benchmark_file': workDir + runLocationRISC + f'{slash}RISC{slash}renaissanceOutput_risc.csv',
        'processor': 'RISC-V',
        'benchmark': 'Idle',
        'color': '0.6'
    },
    {
        'power_file': workDir + runLocationRISCInclMeasurements + f'{slash}RISC{slash}shellyReaderResults_risc',
        'rapl_file': None,
        'benchmark_file': workDir + runLocationRISCInclMeasurements + f'{slash}RISC{slash}renaissanceOutput_risc.csv',
        'processor': 'RISC-V',
        'benchmark': 'ProcFS Measurements',
        'color': '0.8'
    }
]

# Liste für alle eingelesenen Dataframes
all_power_data = []
rapl_energy = 0;

# Einlesen aller Dateipaare
for source in data_sources:
    combined_power_data = []

    # Einlesen power_file (ProcFS-Daten)
    power_data = pd.read_csv(
        source['power_file'],
        header=None,
        names=['ip', 'timestamp_s', 'power', 'unknown'],
        na_values=[''],
        skip_blank_lines=True
    )
    power_data = power_data.dropna()


    # Neue Auswahl: überspringe die ersten 60 Zeilen, verwende die nächsten 480
    power_data = power_data.iloc[60:60+480]

    # Check if exactly 480 values (8 minutes) are present
    if len(power_data) != 480:
        print(f"Warnung: Es wurden {len(power_data)} Werte gefunden (erwartet: 480)." + source['power_file'])

    power_data['processor'] = source['processor']

    power_data['benchmark'] = source['benchmark'] + '\n(Energy Meter)'
    combined_power_data.append(power_data[['power', 'processor', 'benchmark']])

    # Falls rapl_file vorhanden ist, einlesen und verarbeiten
    if source.get('rapl_file'):
        rapl_data = pd.read_csv(
            source['rapl_file'],
            header=0,  # erste Zeile ist Header
            skip_blank_lines=True
        )

        # Zeitbasierte Filterung der RAPL-Daten (Timestamp in ms)
        max_timestamp = rapl_data['Timestamp'].max()
        rapl_data['Timestamp'] = max_timestamp - rapl_data['Timestamp']
        rapl_data = rapl_data[(rapl_data['Timestamp'] >= 60000) & (rapl_data['Timestamp'] <= 540000)]

        # Nur die Zeilen mit gültigen Leistungswerten behalten
        rapl_data = rapl_data[['Power (Watts)', 'DRAM Power (Watts)', ' Energy (micro joules)']].dropna()

        rapl_energy = (rapl_data[' Energy (micro joules)'].max() - rapl_data[' Energy (micro joules)'].min()) / 1_000_000

        # Summiere Package- und DRAM-Leistung
        rapl_data['power'] = rapl_data['Power (Watts)']  #+ rapl_data['DRAM Power (Watts)']
        rapl_data['processor'] = source['processor']
        rapl_data['benchmark'] = source['benchmark'] + '\n(RAPL)'
        combined_power_data.append(rapl_data[['power', 'processor', 'benchmark']])

    # Alle relevanten Daten zusammenfassen
    all_power_data.extend(combined_power_data)

print("\n--- Durchschnittliche Power-Werte (Watt) ---")
for df in all_power_data:
    benchmark = df['benchmark'].iloc[0]
    mean_power = df['power'].mean()
    print(f"{benchmark}: {mean_power:.4f} W")

# Gruppieren der Daten nach Prozessor
x86_data = [data for data in all_power_data if (data['processor'] == 'X86').all()]
riscv_data = [data for data in all_power_data if (data['processor'] == 'RISC-V').all()]

plt.rcParams['font.size'] = '16'
fig, axes = plt.subplots(1, 2, figsize=(16, 8), dpi=300)

# X86 Boxplot
data_to_plot_x86 = [df['power'] for df in x86_data]
labels_x86 = [df['benchmark'].iloc[0] for df in x86_data]
colors_x86 = ['0.2', '0.4', '0.4']  # Farbe für RAPL = gleiche Farbe wie zugehörige Messung

boxplot_x86 = axes[0].boxplot(data_to_plot_x86, tick_labels=labels_x86, patch_artist=True)
for patch, color in zip(boxplot_x86['boxes'], colors_x86):
    patch.set_facecolor(color)
for median in boxplot_x86['medians']:
    median.set(color='black', linewidth=2)
for i, data in enumerate(data_to_plot_x86, start=1):
    mean = data.mean()
    axes[0].text(i, mean, 'x', horizontalalignment='center', color='red')
axes[0].set_ylabel('Power Consumption (W)')
axes[0].set_title('X86 Power Consumption')
axes[0].grid(True)

# RISC-V Boxplot
data_to_plot_riscv = [df['power'] for df in riscv_data]
labels_riscv = [df['benchmark'].iloc[0] for df in riscv_data]
colors_riscv = ['0.6', '0.8']

boxplot_riscv = axes[1].boxplot(data_to_plot_riscv, tick_labels=labels_riscv, patch_artist=True)
for patch, color in zip(boxplot_riscv['boxes'], colors_riscv):
    patch.set_facecolor(color)
for median in boxplot_riscv['medians']:
    median.set(color='black', linewidth=2)
for i, data in enumerate(data_to_plot_riscv, start=1):
    mean = data.mean()
    axes[1].text(i, mean, 'x', horizontalalignment='center', color='red')
axes[1].set_ylabel('Power Consumption (W)')
axes[1].set_title('RISC-V Power Consumption')
axes[1].grid(True)
# ... (dein bisheriger Code bleibt unverändert bis einschließlich plt.subplots)

# Nach dem Erstellen der Boxplots für X86 und RISC-V:

# Summen berechnen
x86_sums = []
for df in x86_data:
    benchmark_label = df['benchmark'].iloc[0]
    if '(RAPL)' in benchmark_label:
        # Verwende den bereits berechneten rapl_energy
        x86_sums.append(rapl_energy)
    else:
        x86_sums.append(df['power'].sum())

riscv_sums = [df['power'].sum() for df in riscv_data]

# Tabellen unterhalb der Boxplots einfügen
# X86 Tabelle
cell_text_x86 = [[f"{val:.2f} Joule"] for val in x86_sums]
row_labels_x86 = [df['benchmark'].iloc[0].replace('\n(RAPL)', ' (RAPL)').replace('\n(Energy Meter)', ' (Energy Meter)') for df in x86_data]
table_x86 = axes[0].table(
    cellText=cell_text_x86,
    rowLabels=row_labels_x86,
    colLabels=["X86 Energy Consumption"],
    cellLoc='center',
    rowLoc='center',
    loc='bottom',
    bbox=[0.55, -0.7, 0.5, 0.5]
)
table_x86.auto_set_font_size(False)
table_x86.set_fontsize(16)
#table_x86.scale(1.5, 3.5)
# RISC-V Tabelle
cell_text_riscv = [[f"{val:.2f} Joule"] for val in riscv_sums]
row_labels_riscv = [df['benchmark'].iloc[0] for df in riscv_data]
table_riscv = axes[1].table(
    cellText=cell_text_riscv,
    rowLabels=row_labels_riscv,
    colLabels=["RISC-V Energy Consumption"],
    cellLoc='center',
    rowLoc='center',
    loc='bottom',
    bbox=[0.45, -0.7, 0.5, 0.5]
)
table_riscv.auto_set_font_size(False)
table_riscv.set_fontsize(16)
#table_riscv.scale(1.5, 2.5)

# Layout anpassen
plt.tight_layout()
plt.subplots_adjust(bottom=0.4)  # Platz für Tabellen schaffen
plt.savefig('idle_power_consumption_comparison_with_sums.pdf', format='pdf', bbox_inches='tight')


#plt.show()

