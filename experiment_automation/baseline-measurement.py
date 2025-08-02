import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from enum import Enum
from os.path import abspath, dirname

import paramiko
from dotenv import load_dotenv

load_dotenv("benchmark.env")
# Configuration
MEASUREMENT_DURATION = 12 * 60  # 12 minutes, cut to desired duration
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
    ],
)
JARS = {
    APPS.SHELLY: "shelly-power-reader-1.0-runner.jar",
    APPS.PROCFS: "procfs-reader-1.0-runner.jar",
    APPS.RAPL: "powercap-reader-1.0-runner.jar",
}
OUTPUT_FILE_NAMES = {
    APPS.SHELLY: "shellyReaderResults",
    APPS.RAPL: "raplResults",
    APPS.PROCFS: "procfsResults",
}
POSTFIX = {MACHINE.X86: "_x86", MACHINE.RISC: "_risc"}
SHELLY_VERSION = {MACHINE.X86: "1", MACHINE.RISC: "2+"}

USE_JBOSS_ARG = "-Djava.util.logging.manager=org.jboss.logmanager.LogManager"

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
            results_folder,
            remote_basefolder_name,
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
        self.results_folder = f"{results_folder}/{machine.name}"
        self.remote_base_folder = f"/home/{user}/{remote_basefolder_name}"
        self.remote_dir = f"{self.remote_base_folder}/{results_folder}"
        self.shelly_process = None
        self.ssh_client = None
        self.exception = None

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
                USE_JBOSS_ARG,
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
            start_time = time.time()
            self.shelly_process = subprocess.Popen(
                shelly_cmd,
                cwd=self.results_folder,
                stdout=open(shelly_log_path, "x"),
                stderr=subprocess.STDOUT,
            )
            time.sleep(MEASUREMENT_DURATION)
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


def main():
    # Add signal handler for interrupt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get nproc for remote machines

    # Set up results folder
    date_str = time.strftime("%d-%m-%Y")
    time_str = time.strftime("%H-%M-%S")

    # Create results folder
    logging.info(f"Running baseline measurement")
    results_folder = f"baseline-measurement/{date_str}{time_str}"
    os.makedirs(results_folder, exist_ok=True)

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
        results_folder,
        "baseline-measurement",
    )
    x86 = BenchmarkWorker(
        MACHINE.X86,
        X86_IP,
        X86_USER,
        SSH_KEY_X86,
        SHELLY_X86_IP,
        SHELLY_X86_PW,
        8080,
        SHELLY_VERSION[MACHINE.X86],
        results_folder,
        "baseline-measurement",
    )

    x86.start()
    risc.start()
    x86.join()
    risc.join()
    # Exit early if any worker encountered an error
    if risc.exception:
        sys.exit(1)
    logging.info(f"Finished baseline measurement")


if __name__ == "__main__":
    main()
