"""Network latency measurement helpers for the validator.

`NetworkMonitorMixin` provides ping-based latency measurement used when the
validator submits self-monitoring metrics. Kept separate from the core
validator logic since it only shells out to ``ping`` and parses the output.
"""

import platform
import re
import subprocess

from bittensor import logging


class NetworkMonitorMixin:
    """Ping-based network latency measurement."""

    def _measure_network_latency(
        self, target_host: str = "8.8.8.8", timeout: int = 3
    ) -> float:
        """Measure network latency by ping test"""
        backup_hosts = (
            ["1.1.1.1", "8.8.4.4"] if target_host == "8.8.8.8" else ["8.8.8.8"]
        )

        latency = self._ping_host(target_host, timeout)
        if latency > 0:
            return latency

        for backup_host in backup_hosts:
            latency = self._ping_host(backup_host, timeout)
            if latency > 0:
                logging.debug(
                    (
                        f"Primary target {target_host} failed,"
                        f"using backup target {backup_host}"
                    )
                )
                return latency

        return 0.0

    def _ping_host(self, target_host: str, timeout: int) -> float:
        """Execute ping command and return latency in milliseconds"""
        try:
            if platform.system().lower() == "windows":
                # Windows: ping -n 1 -w 3000 8.8.8.8
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), target_host]
            else:
                # Linux/Unix: ping -c 1 -W 3 8.8.8.8
                cmd = ["ping", "-c", "1", "-W", str(timeout), target_host]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 1
            )

            if result.returncode == 0:
                output = result.stdout

                # ParsepingResultGetDelayTime
                if platform.system().lower() == "windows":
                    match = re.search(r"[Time=time=](\d+)ms", output, re.IGNORECASE)
                    if match:
                        return float(match.group(1))
                else:
                    match = re.search(r"time=(\d+\.?\d*).*ms", output)
                    if match:
                        return round(float(match.group(1)), 2)

            return 0.0

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            Exception,
        ) as e:
            logging.debug(f"ping {target_host} Failure: {e}")
            return 0.0
