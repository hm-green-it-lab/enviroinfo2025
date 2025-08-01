import os
import pandas as pd
import matplotlib.pyplot as plt

work_dir = "./"
run_location_x86 = "baseline-measurement_shelly-only\\05-06-202523-33-39"
run_location_x86_with_measurements = "baseline-measurement\\05-06-202511-18-36"
run_location_risc = "baseline-measurement_shelly-only\\05-06-202523-33-39"
run_location_risc_with_measurements = "baseline-measurement\\05-06-202511-18-36"
slash = '\\' if os.name == 'nt' else '/'

# Definition of file pairs to be read
data_sources = [
    {
        'power_file': work_dir + run_location_x86 + f'{slash}X86{slash}shellyReaderResults_x86',
        'rapl_file': None,  # no RAPL in this case
        'benchmark_file': work_dir + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv',
        'processor': 'x86',
        'benchmark': 'Idle',
        'color': '0.2'
    },
    {
        'power_file': work_dir + run_location_x86_with_measurements + f'{slash}X86{slash}shellyReaderResults_x86',
        'rapl_file': work_dir + run_location_x86_with_measurements + f'{slash}X86{slash}raplResults_x86',
        'benchmark_file': work_dir + run_location_x86_with_measurements + f'{slash}X86{slash}renaissanceOutput_x86.csv',
        'processor': 'x86',
        'benchmark': 'ProcFS and RAPL \nMeasurements',
        'color': '0.4'
    },
    {
        'power_file': work_dir + run_location_risc + f'{slash}RISC{slash}shellyReaderResults_risc',
        'rapl_file': None,
        'benchmark_file': work_dir + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv',
        'processor': 'RISC-V',
        'benchmark': 'Idle',
        'color': '0.6'
    },
    {
        'power_file': work_dir + run_location_risc_with_measurements + f'{slash}RISC{slash}shellyReaderResults_risc',
        'rapl_file': None,
        'benchmark_file': work_dir + run_location_risc_with_measurements + f'{slash}RISC{slash}renaissanceOutput_risc.csv',
        'processor': 'RISC-V',
        'benchmark': 'ProcFS Measurements',
        'color': '0.8'
    }
]

# List to hold all loaded DataFrames
all_power_data = []
rapl_energy = 0

# Load all file pairs
for source in data_sources:
    combined_power_data = []

    # Load power_file (ProcFS data)
    power_data = pd.read_csv(
        source['power_file'],
        header=None,
        names=['ip', 'timestamp_s', 'power', 'unknown'],
        na_values=[''],
        skip_blank_lines=True
    )
    power_data = power_data.dropna()

    # New selection: skip the first 60 lines, use the next 480
    power_data = power_data.iloc[60:60 + 480]

    # Check if exactly 480 values (8 minutes) are present
    if len(power_data) != 480:
        print(f"Warning: Found {len(power_data)} values (expected: 480). " + source['power_file'])

    power_data['processor'] = source['processor']
    power_data['benchmark'] = source['benchmark'] + '\n(EM)'
    combined_power_data.append(power_data[['power', 'processor', 'benchmark']])

    # If rapl_file is present, read and process it
    if source.get('rapl_file'):
        rapl_data = pd.read_csv(
            source['rapl_file'],
            header=0,
            skip_blank_lines=True
        )

        # Time-based filtering of RAPL data (timestamp in ms)
        max_timestamp = rapl_data['Timestamp'].max()
        rapl_data['Timestamp'] = max_timestamp - rapl_data['Timestamp']
        rapl_data = rapl_data[(rapl_data['Timestamp'] >= 60000) & (rapl_data['Timestamp'] <= 540000)]

        # Keep only rows with valid power values
        rapl_data = rapl_data[['Power (Watts)', 'DRAM Power (Watts)', ' Energy (micro joules)']].dropna()

        rapl_energy = (rapl_data[' Energy (micro joules)'].max() - rapl_data[' Energy (micro joules)'].min()) / 1_000_000

        # Sum package and DRAM power
        rapl_data['power'] = rapl_data['Power (Watts)']  # + rapl_data['DRAM Power (Watts)']
        rapl_data['processor'] = source['processor']
        rapl_data['benchmark'] = source['benchmark'] + '\n(RAPL)'
        combined_power_data.append(rapl_data[['power', 'processor', 'benchmark']])

    # Collect all relevant data
    all_power_data.extend(combined_power_data)

print("\n--- Average Power Values (Watts) ---")
for df in all_power_data:
    benchmark = df['benchmark'].iloc[0]
    mean_power = df['power'].mean()
    print(f"{benchmark}: {mean_power:.4f} W")

# Group data by processor
x86_data = [data for data in all_power_data if (data['processor'] == 'x86').all()]
riscv_data = [data for data in all_power_data if (data['processor'] == 'RISC-V').all()]

plt.rcParams['font.size'] = '16'
fig, axes = plt.subplots(1, 2, figsize=(16, 8), dpi=300)

# x86 boxplot
data_to_plot_x86 = [df['power'] for df in x86_data]
labels_x86 = [df['benchmark'].iloc[0] for df in x86_data]
colors_x86 = ['0.2', '0.4', '0.4']  # color for RAPL = same as corresponding measurement

boxplot_x86 = axes[0].boxplot(data_to_plot_x86, tick_labels=labels_x86, patch_artist=True)
for patch, color in zip(boxplot_x86['boxes'], colors_x86):
    patch.set_facecolor(color)
for median in boxplot_x86['medians']:
    median.set(color='black', linewidth=2)
for i, data in enumerate(data_to_plot_x86, start=1):
    mean = data.mean()
    axes[0].text(i, mean, 'x', horizontalalignment='center', color='red')
axes[0].set_ylabel('Power Consumption (W)')
axes[0].set_title('x86 Power Consumption')
axes[0].grid(True)

# RISC-V boxplot
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

# Calculate energy sums
x86_sums = []
for df in x86_data:
    benchmark_label = df['benchmark'].iloc[0]
    if '(RAPL)' in benchmark_label:
        x86_sums.append(rapl_energy)
    else:
        x86_sums.append(df['power'].sum())

riscv_sums = [df['power'].sum() for df in riscv_data]

# Add tables below boxplots
# x86 table
cell_text_x86 = [[f"{val:.2f} Joule"] for val in x86_sums]
row_labels_x86 = [df['benchmark'].iloc[0].replace('\n(RAPL)', ' (RAPL)').replace('\n(EM)', ' (EM)') for df in x86_data]
table_x86 = axes[0].table(
    cellText=cell_text_x86,
    rowLabels=row_labels_x86,
    colLabels=["x86 Energy Consumption"],
    cellLoc='center',
    rowLoc='center',
    loc='bottom',
    bbox=[0.45, -0.7, 0.5, 0.5]
)
table_x86.auto_set_font_size(False)
table_x86.set_fontsize(16)

# RISC-V table
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

# Adjust layout
plt.tight_layout()
plt.subplots_adjust(bottom=0.4)  # Make space for tables
plt.savefig('idle_power_consumption_comparison_with_sums.pdf', format='pdf', bbox_inches='tight')

# plt.show()