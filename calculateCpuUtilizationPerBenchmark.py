import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, List

work_dir = "./"
run_location_x86 = "_CPU100\\06-06-202512-59-33"
#run_location_x86 = "-DISABLED_TURBO_CPU100\\06-06-202516-20-40"
run_location_risc = "_CPU100\\06-06-202512-59-33"
#run_location_risc = "_CORE-LIMITED-CPU-4\\03-06-202523-12-41"

def calculate_cpu_usage(renaissance_file, procfs_file, benchmark_name, processor, benchmark_start_index=0):
    try:
        # Read Renaissance output CSV
        ren_df = pd.read_csv(renaissance_file)

        # Filter for the specific benchmark and start index
        benchmark_data = ren_df[ren_df['benchmark'] == benchmark_name]
        if benchmark_data.empty:
            raise ValueError(f"Benchmark '{benchmark_name}' not found in data!")

        # Ensure the start index is valid
        if benchmark_start_index >= len(benchmark_data):
            raise ValueError(f"Start index {benchmark_start_index} is too large for benchmark '{benchmark_name}'")

        # Filter from the desired start index
        benchmark_data = benchmark_data.iloc[benchmark_start_index:]

        # Compute start and end time
        start_time = benchmark_data.iloc[0]['vm_start_unix_ms'] + benchmark_data.iloc[0]['uptime_ns'] / 1_000_000
        end_time = benchmark_data.iloc[-1]['vm_start_unix_ms'] + benchmark_data.iloc[-1]['uptime_ns'] / 1_000_000

        # Read procfs results
        proc_df = pd.read_csv(procfs_file)

        # Filter for /proc/stat entries and time window
        proc_df = proc_df[
            (proc_df['SourceFile'].str.match(r'/proc/\d+/stat')) &
            (proc_df['Timestamp'] >= start_time) &
            (proc_df['Timestamp'] <= end_time)
            ]

        # Calculate CPU usage
        cpu_cores = 8 if processor == 'RISC-V' else 4
        ticks_per_second = 100

        # Compute differences between consecutive measurements
        proc_df['userTime_diff'] = proc_df['userTime (Ticks)'].diff()
        proc_df['systemTime_diff'] = proc_df['systemTime (Ticks)'].diff()
        proc_df['timestamp_diff'] = proc_df['Timestamp'].diff() / 1000

        # Drop first row (NaN from diff)
        proc_df = proc_df.dropna()

        # Compute CPU utilization in percent
        total_cpu_usage = ((proc_df['userTime_diff'] + proc_df['systemTime_diff']) /
                           (proc_df['timestamp_diff'] * ticks_per_second * cpu_cores)) * 100

        # Add CPU usage values to the DataFrame
        proc_df['cpu_usage'] = total_cpu_usage

        # Calculate relative seconds since start
        proc_df['relative_seconds'] = np.floor((proc_df['Timestamp'] - proc_df['Timestamp'].iloc[0]) / 1000)

        # Group values per second
        cpu_per_second = proc_df.groupby('relative_seconds')['cpu_usage'].agg(list).reset_index()

        return {
            'benchmark': benchmark_name,
            'start_index': benchmark_start_index,
            'average_cpu_usage': total_cpu_usage.mean(),
            'max_cpu_usage': total_cpu_usage.max(),
            'min_cpu_usage': total_cpu_usage.min(),
            'start_time': start_time,
            'end_time': end_time,
            'num_measurements': len(proc_df),
            'cpu_values_per_second': [val for sublist in cpu_per_second['cpu_usage'].tolist() for val in sublist]
        }
    except Exception as e:
        print(f"Error while processing benchmark {benchmark_name}: {str(e)}")
        return None

def plot_cpu_usage_boxplots_comparison(all_results: List[Dict]):
    """
    Creates boxplots for each benchmark in the style of the visualizeDurationAsBoxplots script.
    """
    # Group results by benchmark name
    benchmark_groups = {}
    for result in all_results:
        if result is not None:
            benchmark_name = result['benchmark']
            if benchmark_name not in benchmark_groups:
                benchmark_groups[benchmark_name] = []
            benchmark_groups[benchmark_name].append(result)

    # Define font sizes
    TITLE_SIZE = 20
    LABEL_SIZE = 20
    TICK_SIZE = 16

    # Set global font size
    plt.rcParams.update({
        'font.size': TICK_SIZE,
        'axes.titlesize': TITLE_SIZE,
        'axes.labelsize': LABEL_SIZE,
        'xtick.labelsize': TICK_SIZE,
        'ytick.labelsize': TICK_SIZE
    })

    num_benchmarks = len(benchmark_groups)

    # Create figure with subplots
    fig, axes = plt.subplots(1, num_benchmarks, figsize=(20, 6), sharey=True)
    if num_benchmarks == 1:
        axes = [axes]

    # Define grayscale palette
    palette = sns.color_palette("Greys", n_colors=2)

    # Create a separate plot for each benchmark
    for idx, (benchmark_name, results) in enumerate(benchmark_groups.items()):
        plot_data = []
        processors = []
        for result in results:
            plot_data.extend(result['cpu_values_per_second'])
            processors.extend([result['processor']] * len(result['cpu_values_per_second']))

        df = pd.DataFrame({
            'CPU Utilization (%)': plot_data,
            'Processor': processors
        })

        # Create boxplot
        sns.boxplot(x='Processor', y='CPU Utilization (%)', data=df,
                    palette=palette, ax=axes[idx])

        # Format subplot
        axes[idx].set_title(benchmark_name, fontsize=TITLE_SIZE, pad=15)
        axes[idx].set_xlabel('')
        if idx == 0:
            axes[idx].set_ylabel('CPU Utilization (%)', fontsize=LABEL_SIZE)
        else:
            axes[idx].set_ylabel('')

        axes[idx].tick_params(axis='x', rotation=45, labelsize=TICK_SIZE)
        axes[idx].tick_params(axis='y', labelsize=TICK_SIZE)

        axes[idx].yaxis.grid(True)
        axes[idx].set_ylim(0, 100)

    plt.tight_layout(pad=2.0)

    # Save boxplot as PDF
    pdf_path = 'X86' + run_location_x86.replace(slash, "_").replace("/", "_") + '_RISC' + run_location_risc.replace(slash, "_").replace("/", "_") + '_cpuUtilizationBoxplot.pdf'
    #pdf_path = 'frequencyAndCoreMatchedCpuUtilizationBoxplot.pdf'
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight', dpi=300)
    plt.show()

    print(f"Boxplot was successfully saved as PDF: {pdf_path}")

def process_benchmarks(directory_configs, benchmark_configs):
    """
    Processes multiple benchmarks from different directories with processor information.

    :param directory_configs: List of directory configurations with processor info
    :param benchmark_configs: List of dictionaries with benchmark configurations
    """
    all_results = []

    for directory_config in directory_configs:
        directory = directory_config['path']
        processor = directory_config['processor']

        processor_suffix = 'risc' if processor == 'RISC-V' else 'x86'
        renaissance_file = os.path.join(directory, f'renaissanceOutput_{processor_suffix}.csv')
        procfs_file = os.path.join(directory, f'procfsResults_{processor_suffix}')

        if not (os.path.exists(renaissance_file) and os.path.exists(procfs_file)):
            print(f"Skipping non-existent directory: {directory}")
            continue

        for config in benchmark_configs:
            result = calculate_cpu_usage(
                renaissance_file,
                procfs_file,
                benchmark_name=config['name'],
                processor=processor,
                benchmark_start_index=config.get('start_index', 0)
            )
            if result:
                result['processor'] = processor
                all_results.append(result)

    return all_results

# Example run
if __name__ == "__main__":
    slash = '\\' if os.name == 'nt' else '/'
    directory_configs = [
        {
            'path': work_dir + 'gpl-akka-uct' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-akka-uct' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-fj-kmeans' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-fj-kmeans' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-reactors' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-reactors' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-future-genetic' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-future-genetic' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-mnemonics' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-mnemonics' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-par-mnemonics' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-par-mnemonics' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-rx-scrabble' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-rx-scrabble' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
        {
            'path': work_dir + 'gpl-scrabble' + run_location_x86 + slash + 'X86',
            'processor': 'x86'
        },
        {
            'path': work_dir + 'gpl-scrabble' + run_location_risc + slash + 'RISC',
            'processor': 'RISC-V'
        },
    ]

    benchmark_configs = [
        {'name': 'akka-uct', 'start_index': 24},
        {'name': 'fj-kmeans', 'start_index': 30},
        {'name': 'reactors', 'start_index': 10},
        {'name': 'future-genetic', 'start_index': 50},
        {'name': 'mnemonics', 'start_index': 16},
        {'name': 'par-mnemonics', 'start_index': 16},
        {'name': 'rx-scrabble', 'start_index': 80},
        {'name': 'scrabble', 'start_index': 50},
    ]

    try:
        all_results = process_benchmarks(directory_configs, benchmark_configs)

        for result in all_results:
            print(f"\nCPU usage statistics for {result['benchmark']} ({result['processor']}):")
            print(f"Average CPU usage: {result['average_cpu_usage']:.2f}%")
            print(f"Max CPU usage: {result['max_cpu_usage']:.2f}%")
            print(f"Min CPU usage: {result['min_cpu_usage']:.2f}%")
            print(f"Number of measurements: {result['num_measurements']}")

        plot_cpu_usage_boxplots_comparison(all_results)

    except Exception as e:
        print(f"Error: {e}")
