# Raw Result Data: Java Workloads on RISC-V vs. x86 Processors

This repository contains the raw data collected during the experiments presented in the paper _"Evaluating Performance and Energy Efficiency of RISC-V and x86 Processors for Java Workloads"_.
Furthermore, it contains the Python scripts to create the Figures about the result data included in the paper.

The experiments utilize the Renaissance benchmark suite (https://renaissance.dev/), which includes a variety of workloads designed to evaluate different aspects of Java performance.
To focus specifically on CPU performance and energy efficiency, we selected the **concurrency** and **functional** benchmark groups.
Other groups were excluded as they involve workloads that stress additional system resources such as disk or network I/O.

Descriptions of the benchmarks used in each group are provided in the tables below.

## Renaissance Concurrency Benchmark Group

| **Benchmark** | **Repetitions** | **Description** | **Focus** |
|---------------|------------------|------------------|-----------|
| akka-uct | 34 (24 warm-up + 10 steady-state) | Unbalanced Cobwebbed Tree computation using Akka | actors, message-passing |
| fj-kmeans | 40 (30 warm-up + 10 steady-state) | K-Means algorithm using the fork/join framework | task-parallel, concurrent data structures |
| reactors | 20 (10 warm-up + 10 steady-state) | A set of message-passing workloads encoded in the Reactors framework | actors, message-passing, critical sections |

## Renaissance Functional Benchmark Group

| **Benchmark** | **Repetitions** | **Description** | **Focus** |
|---------------|------------------|------------------|-----------|
| future-genetic | 63 (50 warm-up + 13 steady-state) | Genetic algorithm function optimization using Jenetics | task-parallel, contention |
| mnemonics | 26 (16 warm-up + 10 steady-state) | Solves the phone mnemonics problem using JDK streams | data-parallel, memory-bound |
| par-mnemonics | 26 (16 warm-up + 10 steady-state) | Solves the phone mnemonics problem using parallel JDK streams | data-parallel, memory-bound |
| rx-scrabble | 101 (80 warm-up + 21 steady-state) | Solves the Scrabble puzzle using the RxJava framework | streaming |
| scrabble | 63 (50 warm-up + 13 steady-state) | Solves the Scrabble puzzle using JDK Streams | data-parallel, memory-bound |

## Result Directory Structure

For each of the benchmarks you will find a directoy with the following naming pattern in this repository:

    ./gpl-<benchmark_name>_<run_configuration>

The run configuration refers to the configuration of the experiment conducted.

As a first comparison, we ran the benchmarks on both machines while giving them access to the full CPU capacity (i.e., all cores and full clock speed).
The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>_CPU100

In the next step we ran the benchmarks on both machines while disabling the turbo-boost capabilities of the x86 processor as the RISC-V processor does not support this feature.
The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>-DISABLED_TURBO_CPU100

Following this, we disabled four cores on the RISC-V machine as it contains 8 CPU cores, whereas the x86 machine only contains two real cores with four virtual threads.
The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>_CORE-LIMITED-CPU-4

However, before we started with the actual measurements, we measured the baseline power consumption.
The results are contained in the following directory: 

    ./baseline-measurement_shelly-only

Another baseline power consumption was conducted while measurements for proc fs (and RAPL for x86) where active on both machines, the results are contained in the following directory:

    ./baseline-measurement

## Result Directory Content

In each of the result directories you will find the same structure:


```plaintext
./gpl-<benchmark_name>_<run_configuration>/
└── <benchmark_timestamp>/  # Top level directory with the benchmark timestamp.
    ├── bm_params_sysinfo.txt  # Benchmark start parameters and system information
    ├── x86/  # Results depending on the processor type.
    │   ├── procfsResults_x86  # User and system ticks (basis for CPU time calculations) for the overall system (/proc/stat) and the benchmark process (/proc/<pid>/stat)
    │   ├── raplResults_x86  # Only on x86: power and energy measurements for the processor and DRAM package using Intel Running Average Power Limit (RAPL).
    │   ├── renaissanceOutput_x86.csv  # The benchmark results.
    │   └── timer_x86.txt  # Start and end timestamp of the overall run
    └── RISC-V/
        ├── procfsResults_riscv  # User and system ticks (basis for CPU time calculations) for the overall system (/proc/stat) and the benchmark process (/proc/<pid>/stat)
        ├── renaissanceOutput_riscv.csv  # The benchmark results.
        └── timer_riscv.txt  # Start and end timestamp of the overall run
```

## Python Scripts for Generating Figures About the Result Data

This repository also contains three python scripts that have been used to process and visualize the results:

| Script Name | Description |
|-------------|-------------|
| `calculateCpuUtilizationPerBenchmark.py` | This Python script processes the result data for all benchmarks in a specific run configuration, calculates the steady-state, and visualizes the CPU utilization as boxplots. |
| `visualizeDurationAsBoxplots.py` | This Python script processes the result data for all benchmarks in a specific run configuration, calculates the steady-state, and visualizes the benchmark duration as boxplots. |
| `visualizePowerConsumptionAsBoxPlot.py` | This Python script processes the result data of the baseline measurements and visualizes the power consumption as a boxplot and the energy consumption as a table. |

## Measurement Tools

In addition to the python tools listed above, we have used the following Java-based tools for the experiments in this paper, which are also available online:

| Tool                                                   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|--------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| https://github.com/hm-green-it-lab/powercap-reader     | This Java-based powercap-reader continuously reads RAPL data via powercap on Linux. This tool has been used to collect the raplResults-CSV-files for x86. Please note that it has been updated in the meantime so that only the energy values are stored and the power values are calculated afterwards. In the version of the tool used for this paper, the power values were still directly calculated every second and written in the CSV files. |
| https://github.com/hm-green-it-lab/procfs-reader       | This Java-based procfs-reader continuously reads resource demand data for processes from the proc file system on Linux. In this paper it has been used to create the procfsResults-CSV-files containing the CPU demand data of the benchmarking processes and the overall system.                                                                                                                                                                   |
| https://github.com/hm-green-it-lab/shelly-power-reader | This Java-based shelly-power-reade continuously reads power and energy values for shelly devices. It has been used to create the shellyReaderResults-CSV-files.                                                                                                                                                                                                                                                                                     |

## Experiment Automation

In the folder `experiment_automation` you will find a script called `experiment_automation\benchmarkscript.py` that has been used to automate the benchmark execution.
The version of it named `baseline-measurement.py` was used to measure the system at idle state, once with the procfs and rapl [measurement-tools](#measurement-tools) running and once without.
This script should be executed from a local device (e.g., laptop) and connects via SSH and SFTP to the x86 and RISC-V systems to execute the benchmarks and the necessary measurement tools (see [measurement-tools](#measurement-tools)).

To start the script `Python` and the dependencies in `requirements.txt` are required.
The Nix flake can be used to get a Shell with the required dependencies.
To use a nix flake, nix package manager, or Nixos is required (https://nixos.org/download/).
Then simply run `nix develop` in the `experiment_automation` directory to get a shell with all required dependencies (in some instances `--experimental-features nix-command --extra-perimental-features flakes` needs to be added to the nix develop command).
Furthermore, please note that the `experiment_automation/flake.nix` contains a system property that needs to be adjusted in case 

The `experiment_automation\benchmarkscript.py` script expects the shellyReader to be at `../tools/shelly-power-reader/target/`.
And for the remote machines to have rapl/procfs/renaissance runners in their respective directories.
Also a file `benchmark.env` is required, for necessary variables and their names, check the script.

Once the nix environment is up and running and the benchmark.env is filled with the appropriate values you can run the benchmarks using `python benchmarkscript.py`

## Threads to Validity

- **Comparability of the RISC-V and x86 systems:** This experiment compares an x86 processor contained in a laptop computer with a RISC-V system on a chip (SoC) in a desktop form factor.
Due to the different types of hardware, the two systems have different power supply units.
To account for these differences, we measure the idle power consumption of the entire system and calculate the processor power consumption by subtracting the idle power from the actual power consumption during benchmark execution, which reflects the processor's actual usage.
Consequently, we cannot differentiate the RISC-V processor's idle power consumption from that of the entire system.
To address this, we measured the actual processor power consumption of the x86 processor using RAPL and compared it with values derived from calculated processor power consumption based on system-wide measurements.
As these values match quite well, we believe that the processor power consumption calculation based on the system-wide measurements is an appropriate estimate.
- **Energy measurements:** Even though the shelly energy meters used in the experiment provide total energy values we use instantaneous power values measured every second instead.
The energy values provided by the shelly devices are found in the last column of the shellyReaderResult CSV files (e.g. the value of 25940 in the following line: 10.19.71.4, 17492075749, 9.9, 25940), and are derived from the 'energy.total' value provided by the Shelly devices (https://shelly-api-docs.shelly.cloud/gen2/General/RPCProtocol#notification-frame).
Unfortunately, this value was too imprecise for our measurements.
It seems to be measured in watt-hours (https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/#response-2) and as you can see, it doesn't really change much in most files, which is why we use the instantaneous power value instead.
This can lead to problems, as we might miss peaks between the measurement probes.
However, as the power measurement results are quite stable across multiple benchmark runs, it seems as if no major peaks have happened.
- **CPU utilization variance:** The akka-uct and reactors benchmarks demonstrate significant variability in CPU utilization.
While the akka-uct benchmark primarily exhibits this behavior in the context of RISC-V, the reactors benchmark also demonstrates this phenomenon in both the x86 and RISC-V systems.
It is important to note that both energy consumption and benchmark duration are influenced by CPU utilization.
Consequently, the observed variability can result in unstable outcomes for the aforementioned benchmarks.
However, the duration and energy efficiency results demonstrate notable stability for both benchmarks.