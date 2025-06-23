import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

work_dir = "./"
run_location_x86 = "_CPU100\\06-06-202512-59-33"
# run_location_x86 = "-DISABLED_TURBO_CPU100\\06-06-202516-20-40"
run_location_risc = "_CPU100\\06-06-202512-59-33"
# run_location_risc = "_CORE-LIMITED-CPU-4\\03-06-202523-12-41"

slash = '\\' if os.name == 'nt' else '/'

# Example data for CSV files and their dimensions
csv_files = [
    {'file': work_dir + 'gpl-akka-uct' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'akka-uct'},
    {'file': work_dir + 'gpl-akka-uct' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'akka-uct'},

    {'file': work_dir + 'gpl-fj-kmeans' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'fj-kmeans'},
    {'file': work_dir + 'gpl-fj-kmeans' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'fj-kmeans'},

    {'file': work_dir + 'gpl-reactors' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'reactors'},
    {'file': work_dir + 'gpl-reactors' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'reactors'},

    {'file': work_dir + 'gpl-future-genetic' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'future-genetic'},
    {'file': work_dir + 'gpl-future-genetic' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'future-genetic'},

    {'file': work_dir + 'gpl-mnemonics' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'mnemonics'},
    {'file': work_dir + 'gpl-mnemonics' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'mnemonics'},

    {'file': work_dir + 'gpl-par-mnemonics' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'par-mnemonics'},
    {'file': work_dir + 'gpl-par-mnemonics' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'par-mnemonics'},

    {'file': work_dir + 'gpl-rx-scrabble' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'rx-scrabble'},
    {'file': work_dir + 'gpl-rx-scrabble' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'rx-scrabble'},

    {'file': work_dir + 'gpl-scrabble' + run_location_x86 + f'{slash}X86{slash}renaissanceOutput_x86.csv', 'processor': 'x86', 'run': 'scrabble'},
    {'file': work_dir + 'gpl-scrabble' + run_location_risc + f'{slash}RISC{slash}renaissanceOutput_risc.csv', 'processor': 'RISC-V', 'run': 'scrabble'},
]

# List to collect data
data_list = []

# Dictionary for rows to skip per run
skip_rows = {
    'akka-uct': 24,
    'fj-kmeans': 30,
    'reactors': 10,
    'future-genetic': 50,
    'mnemonics': 16,
    'par-mnemonics': 16,
    'rx-scrabble': 80,
    'scrabble': 50
}

# Read CSV files and prepare data
for file_info in csv_files:
    # Determine number of rows to skip based on run
    rows_to_skip = skip_rows.get(file_info['run'], 0)

    # Read CSV, skipping the defined rows
    df = pd.read_csv(file_info['file'],
                     index_col=None,
                     header=0,
                     skiprows=range(1, rows_to_skip + 1))  # +1 because range is exclusive

    # Find minimum timestamp
    min_timestamp = df['uptime_ns'].min()

    # Make timestamps relative to the minimum timestamp
    df['uptime_ns'] = df['uptime_ns'] - min_timestamp

    df['duration_s'] = df['duration_ns'] / 1_000_000_000

    # Add processor and benchmark run info
    df['processor'] = file_info['processor']
    df['run'] = file_info['run']

    # Append to data list
    data_list.append(df)

# Combine all data into one DataFrame
df = pd.concat(data_list, axis=0, ignore_index=True)

# Group data by timestamp, processor, and run
agg_df = df.groupby(['duration_s', 'processor', 'run']).all().reset_index()

# Define benchmark run order
benchmark_order = ['akka-uct', 'fj-kmeans', 'reactors', 'future-genetic', 'mnemonics', 'par-mnemonics', 'rx-scrabble', 'scrabble']

# Define font sizes
TITLE_SIZE = 20
LABEL_SIZE = 20
TICK_SIZE = 16

# Set global font sizes for matplotlib
plt.rcParams.update({
    'font.size': TICK_SIZE,
    'axes.titlesize': TITLE_SIZE,
    'axes.labelsize': LABEL_SIZE,
    'xtick.labelsize': TICK_SIZE,
    'ytick.labelsize': TICK_SIZE
})

# Number of benchmarks
n_benchmarks = len(benchmark_order)

# Create figure with subplots
fig, axes = plt.subplots(1, n_benchmarks, figsize=(20, 6), sharey=False)

# Define grayscale palette
palette = sns.color_palette("Greys", n_colors=2)

# Create individual plots for each benchmark
for idx, benchmark in enumerate(benchmark_order):
    # Filter data for current benchmark
    benchmark_data = df[df['run'] == benchmark]

    # Create boxplot
    sns.boxplot(x='processor', y='duration_s', data=benchmark_data,
                palette=palette, ax=axes[idx])
    axes[idx].set_ylim(bottom=0)

    # Format subplot
    axes[idx].set_title(benchmark, fontsize=TITLE_SIZE, pad=15)
    axes[idx].set_xlabel('')
    if idx == 0:
        axes[idx].set_ylabel('Duration (s)', fontsize=LABEL_SIZE)
    else:
        axes[idx].set_ylabel('')

    # Rotate x-axis labels and set tick size
    axes[idx].tick_params(axis='x', rotation=45, labelsize=TICK_SIZE)
    axes[idx].tick_params(axis='y', labelsize=TICK_SIZE)

    # Add grid lines
    axes[idx].yaxis.grid(True)

# Optimize layout with padding
plt.tight_layout(pad=2.0)

# Save boxplot as PDF
pdf_path = 'X86' + run_location_x86.replace(slash, "_").replace("/", "_") + '_RISC' + run_location_risc.replace(slash, "_").replace("/", "_") + '_durationBoxplot.pdf'
# pdf_path = 'frequencyAndCoreMatchedDurationBoxplot.pdf'
plt.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)

# Show boxplot
plt.show()

print(f"Boxplot was successfully saved as PDF: {pdf_path}")
