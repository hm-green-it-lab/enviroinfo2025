import os
import shutil
import sys
import signal
import threading
import subprocess
import time
import logging
from os.path import abspath, dirname

import paramiko

from dotenv import load_dotenv
from enum import Enum

load_dotenv("benchmark.env")
# Configuration
BENCHMARKS = [  # Running these sequentially
    # Functional
    "JmhFutureGenetic",
    "JmhMnemonics",
    "JmhParMnemonic",
    "JmhRxScrabble",
    "JmhScrabble",
    # Concurrency
    "JmhReactors",  # Timed out on risc.
    "JmhAkkaUct",  # these two should be in concurrency, but ran already. This had nullpointers.
    "JmhFjKmeans",
]
CPU_UTILIZATION = [100, 75, 50, 25]  # Array of CPU percentages to run
JVM_ARGS = "--add-opens java.base/sun.nio.ch=ALL-UNNAMED --add-opens java.base/java.nio=ALL-UNNAMED --add-opens java.base/java.lang.invoke=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED -Djmh.blackhole.mode=COMPILER"
BM_MODE = "Throughput"
TIME_UNIT = "s"
STATIC_BM_PARAMS = f"-bm {BM_MODE} -tu {TIME_UNIT} -f 1 -t 1"
MACHINE = Enum(
    "MACHINE",
    [
        "RISC",
        "X86",
    ],
)
APPS = Enum(
    "APPS",
    [
        "SHELLY",
        "PROCFS",
        "RAPL",
        "RENAISSANCE",
    ],
)
JARS = {
    APPS.SHELLY: "shelly-power-reader-1.0-runner.jar",
    APPS.RENAISSANCE: "renaissance-jmh-0.16.0.jar",
    APPS.PROCFS: "procfs-reader-1.0-runner.jar",
    APPS.RAPL: "powercap-reader-1.0-runner.jar",
}
OUTPUT_FILE_NAMES = {
    APPS.SHELLY: "shellyReaderResults",
    APPS.PROCFS: "procfsResults",
    APPS.RAPL: "raplResults",
    APPS.RENAISSANCE: "renaissance",
}
POSTFIX = {MACHINE.X86: "_x86", MACHINE.RISC: "_risc"}
SHELLY_VERSION = {MACHINE.X86: "1", MACHINE.RISC: "2+"}

RISC_IP = os.environ.get("RISC_IP")
X86_IP = os.environ.get("X86_IP")
RISC_USER = os.environ.get("RISC_USER")
X86_USER = os.environ.get("X86_USER")
SSH_KEY_RISC = os.environ.get("RISC_SSH_KEY")
SSH_KEY_X86 = os.environ.get("X86_SSH_KEY")
SHELLY_RISC_IP = os.environ.get("SHELLY_RISC_IP")
SHELLY_RISC_PW = os.environ.get("SHELLY_RISC_PW")
SHELLY_X86_IP = os.environ.get("SHELLY_X86_IP")
SHELLY_X86_PW = os.environ.get("SHELLY_X86_PW")

# Validate critical environment variables
required_env = [
    RISC_IP,
    X86_IP,
    RISC_USER,
    X86_USER,
    SSH_KEY_RISC,
    SSH_KEY_X86,
    SHELLY_RISC_IP,
    SHELLY_RISC_PW,
    SHELLY_X86_IP,
    SHELLY_X86_PW,
]
if not all(required_env):
    logging.error("One or more required environment variables are not set")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if not (shutil.which("java")):
    logging.error("Java is not installed or not found in PATH")
    sys.exit(1)


def signal_handler(*_):
    logging.info("Termination signal received. Cleaning up...")
    for t in threading.enumerate():
        if isinstance(t, BenchmarkWorker):
            t.cleanup()
    sys.exit(1)


class BenchmarkWorker(threading.Thread):
    def __init__(
            self,
            machine: MACHINE,
            ip,
            user,
            ssh_key,
            shelly_ip,
            shelly_pw,
            shelly_port,
            shelly_version,
            jvm_args,
            bm_params,
            results_folder,
            remote_basefolder_name,
            cpuQuota,
    ):
        super().__init__()
        self.machine = machine
        self.ip = ip
        self.user = user
        self.ssh_key = ssh_key
        self.shelly_ip = shelly_ip
        self.shelly_pw = shelly_pw
        self.shelly_port = shelly_port
        self.shelly_version = shelly_version
        self.jvm_args = jvm_args
        self.bm_params = bm_params
        self.results_folder = f"{results_folder}/{machine.name}"
        self.remote_base_folder = f"/home/{user}/{remote_basefolder_name}"
        self.remote_dir = f"{self.remote_base_folder}/{results_folder}"
        self.shelly_process = None
        self.ssh_client = None
        self.exception = None
        self.cpuQuota = cpuQuota

    def run(self):
        postfix = POSTFIX[self.machine]
        os.makedirs(self.results_folder, exist_ok=True)
        try:
            logging.info(f"[{self.machine}] Starting benchmark worker")

            # 1) start local Shelly reader
            parent_directory = dirname(dirname(abspath(__file__)))
            shelly_log_filename = f"{OUTPUT_FILE_NAMES[APPS.SHELLY]}{postfix}"
            shelly_log_path = os.path.join(self.results_folder, shelly_log_filename)
            shelly_cmd = [
                "java",
                f"-Dquarkus.http.port={self.shelly_port}",
                "-Djava.util.logging.manager=org.jboss.logmanager.LogManager",
                # necessary to prevent error output due to java using a different logger
                "-jar",
                f"{parent_directory}/tools/shelly-power-reader/target/{JARS[APPS.SHELLY]}",
                "-i",
                self.shelly_ip,
                "-p",
                self.shelly_pw,
                "-g",
                self.shelly_version,
            ]
            logging.info(
                f"[{self.machine}] Launching local Shelly reader: {' '.join(shelly_cmd)}"
            )
            self.shelly_process = subprocess.Popen(
                shelly_cmd,
                cwd=self.results_folder,
                stdout=open(shelly_log_path, "x"),
                stderr=subprocess.STDOUT,
            )

            # 2) connect via SSH using Paramiko
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logging.info(f"[{self.machine}] Connecting to {self.ip} as {self.user}")
            self.ssh_client.connect(
                hostname=self.ip,
                username=self.user,
                key_filename=self.ssh_key,
                timeout=10,
            )

            # 3) build remote command
            cmd_parts = [
                f"mkdir -p {self.remote_dir} && cd {self.remote_dir}",
                # start procfs monitor
                f"nohup java -jar {self.remote_base_folder}/{JARS[APPS.PROCFS]} > {OUTPUT_FILE_NAMES[APPS.PROCFS]}{postfix} 2>&1 </dev/null &",
            ]
            # on x86 also start RAPL monitor
            if self.machine == MACHINE.X86:
                cmd_parts.append(
                    f"nohup java -jar {self.remote_base_folder}/{JARS[APPS.RAPL]} > {self.remote_dir}/{OUTPUT_FILE_NAMES[APPS.RAPL]}{postfix} 2>&1 </dev/null &",
                )
            # run the JMH benchmark
            outputArgs = f"-o {self.remote_dir}/{OUTPUT_FILE_NAMES[APPS.RENAISSANCE]}Output{postfix} -rff {self.remote_dir}/{OUTPUT_FILE_NAMES[APPS.RENAISSANCE]}Results{postfix}"
            cmd_parts.append(
                f"systemd-run --scope --user -p CPUQuota={self.cpuQuota}% java {self.jvm_args} -jar /home/{self.user}/renaissance/{JARS[APPS.RENAISSANCE]} {outputArgs} {self.bm_params}"
            )
            # build full remote command string, collapsing any '&;' sequences to '&' to avoid bash syntax errors
            cmd_str = "; ".join(cmd_parts)
            cmd_str = cmd_str.replace("&;", "&")
            remote_cmd = f"{cmd_str}; exit $?"

            logging.info(f"[{self.machine}] Running remote benchmark")
            start_time = time.time()
            stdin, stdout, stderr = self.ssh_client.exec_command(
                remote_cmd, get_pty=True
            )
            logging.info(f"[{self.machine}] Remote command: {remote_cmd}")

            # stream remote stdout
            for line in stdout:
                logging.info(f"[{self.machine}][remote] {line.rstrip()}")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                err = stderr.read().decode().strip()
                logging.error(
                    f"[{self.machine}] Remote benchmark failed (status {exit_status}): {err}"
                )

        except Exception as e:
            self.exception = e
            logging.error(f"[{self.machine}] Exception in run(): {e}", exc_info=True)
        finally:
            end_time = time.time()
            self.cleanup()
            with open(
                    os.path.join(self.results_folder, f"timer{POSTFIX[self.machine]}.txt"),
                    "x",
            ) as f:
                try:
                    f.write(f"{start_time}\n{end_time}")
                except NameError:
                    f.write(f"No start time\n{end_time}")

    def cleanup(self):
        logging.info(f"[{self.machine}] Cleaning up resources")

        # 1) kill local Shelly reader
        if self.shelly_process and self.shelly_process.poll() is None:
            try:
                logging.info(
                    f"[{self.machine}] Killing local Shelly reader (pid={self.shelly_process.pid})"
                )
                self.shelly_process.kill()
            except Exception as e:
                logging.error(
                    f"[{self.machine}] Failed to kill Shelly reader: {e}", exc_info=True
                )

        # 2) kill remote monitors and benchmark
        if self.ssh_client:
            jars_to_kill = [JARS[APPS.RENAISSANCE], JARS[APPS.PROCFS]]
            if self.machine == MACHINE.X86:
                jars_to_kill.append(JARS[APPS.RAPL])
            for jar in jars_to_kill:
                try:
                    logging.info(f"[{self.machine}] Killing remote processes for {jar}")
                    self.ssh_client.exec_command(f"pkill -9 -f {jar}")
                except Exception as e:
                    logging.error(
                        f"[{self.machine}] Error killing remote jar {jar}: {e}",
                        exc_info=True,
                    )

            # 3) fetch all result files via SFTP
            try:
                sftp = self.ssh_client.open_sftp()
                # Copy every file in the remote results folder
                files = []
                try:
                    files = sftp.listdir(self.remote_dir)
                except Exception as e:
                    logging.error(
                        f"[{self.machine}] Failed to list remote directory {self.remote_dir}: {e}",
                        exc_info=True,
                    )
                for fname in files:
                    remote_path = f"{self.remote_dir}/{fname}"
                    local_path = os.path.join(self.results_folder, fname)
                    logging.info(f"[{self.machine}] Downloading {fname}")
                    try:
                        sftp.get(remote_path, local_path)
                    except (paramiko.SSHException, EOFError) as e:
                        logging.warning(
                            f"[{self.machine}] Could not fetch {fname}: {e}. Creating empty file"
                        )
                        open(local_path, "w").close()
                    except Exception as e:
                        logging.error(
                            f"[{self.machine}] Failed to download {fname}: {e}",
                            exc_info=True,
                        )
                sftp.close()
            except Exception as e:
                logging.error(f"[{self.machine}] SFTP error: {e}", exc_info=True)

            # close SSH
            try:
                self.ssh_client.close()
            except Exception:
                pass


def get_remote_nproc(host, user, key) -> int:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, username=user, key_filename=key, timeout=10)
        _, stdout, _ = client.exec_command("nproc")
        out = stdout.read().decode().strip()
        client.close()
        return int(out)
    except Exception as e:
        logging.warning(f"Could not get nproc on {host}: {e}, defaulting to 1")
        return 1


def main():
    # Add signal handler for interrupt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get nproc for remote machines
    cores_risc = get_remote_nproc(RISC_IP, RISC_USER, SSH_KEY_RISC)
    cores_x86 = get_remote_nproc(X86_IP, X86_USER, SSH_KEY_X86)

    # Set up results folder
    date_str = time.strftime("%d-%m-%Y")
    time_str = time.strftime("%H-%M-%S")

    for cpu_pct in CPU_UTILIZATION:
        for bench in BENCHMARKS:
            # Create results folder
            logging.info(f"Running {bench} with CPU {cpu_pct}")
            results_folder = f"{bench}_singleShot_CPU{cpu_pct}/{date_str}{time_str}"
            os.makedirs(results_folder, exist_ok=True)

            # Compute cpuQuota
            cpu_quota_risc = cores_risc * cpu_pct
            cpu_quota_x86 = cores_x86 * cpu_pct
            # Create a file to store the bm params and quota
            with open(os.path.join(results_folder, "bm_params.txt"), "w") as f:
                f.write(f"{STATIC_BM_PARAMS} {bench}\n")
                f.write(f"cpuQuota_risc: {cpu_quota_risc}\n")
                f.write(f"cpuQuota_x86: {cpu_quota_x86}\n")

            # Run benchmarks
            risc = BenchmarkWorker(
                MACHINE.RISC,
                RISC_IP,
                RISC_USER,
                SSH_KEY_RISC,
                SHELLY_RISC_IP,
                SHELLY_RISC_PW,
                8081,
                SHELLY_VERSION[MACHINE.RISC],
                JVM_ARGS,
                f"{STATIC_BM_PARAMS} {bench}",
                results_folder,
                "Benchmark",
                cpu_quota_risc,
            )
            x86 = BenchmarkWorker(
                MACHINE.X86,
                X86_IP,
                X86_USER,
                SSH_KEY_X86,
                SHELLY_X86_IP,
                SHELLY_X86_PW,
                8082,
                SHELLY_VERSION[MACHINE.X86],
                JVM_ARGS,
                f"{STATIC_BM_PARAMS} {bench}",
                results_folder,
                "Benchmark",
                cpu_quota_x86,
            )

            risc.start()
            x86.start()
            risc.join()
            x86.join()
            # Exit early if any worker encountered an error
            if risc.exception or x86.exception:
                sys.exit(1)
            logging.info(f"Finished {bench} with CPU {cpu_pct}")
            time.sleep(30)


if __name__ == "__main__":
    main()
