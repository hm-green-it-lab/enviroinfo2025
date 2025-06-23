# Raw Result Data: Java Workloads on RISC-V vs. x86 Processors

This repository contains the raw data collected during the experiments presented in the paper _"Evaluating Performance and Energy Efficiency of RISC-V and x86 Processors for Java Workloads"_. Furthermore, it contains the Python scripts to create the Figures about the result data included in the paper.

The experiments utilize the Renaissance benchmark suite, which includes a variety of workloads designed to evaluate different aspects of Java performance. To focus specifically on CPU performance and energy efficiency, we selected the **concurrency** and **functional** benchmark groups. Other groups were excluded as they involve workloads that stress additional system resources such as disk or network I/O.

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

As a first comparison, we ran the benchmarks on both machines while giving them access to the full CPU capacity (i.e., all cores and full clock speed). The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>_CPU100

In the next step we ran the benchmarks on both machines while disabling the turbo-boost capabilities of the x86 processor as the RISC-V processor does not support this feature. The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>-DISABLED_TURBO_CPU100

Following this, we disabled four cores on the RISC-V machine as it contains 8 CPU cores, whereas the x86 machine only contains two real cores with four virtual threads. The results for these runs contain the following run_configuration:

    ./gpl-<benchmark_name>_CORE-LIMITED-CPU-4

However, before we started with the actual measurements, we measured the baseline power consumption. The results are contained in the following directory: 

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

