"""
SSH-based monitoring for getting real load average from nodes
"""

import asyncio
import logging
from typing import List, Optional, Tuple

import asyncssh

from ..models.node import NodeInfo
from ..utils.i18n import t


class SSHMonitor:
    """SSH-based monitoring for getting real load average from nodes"""

    def __init__(
        self,
        username: str,
        private_key_path: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 10,
        hosts_mapping: Optional[dict] = None,
    ):
        self.username = username
        self.private_key_path = private_key_path
        self.password = password
        self.timeout = timeout
        self.hosts_mapping = hosts_mapping or {}

        if not private_key_path and not password:
            logging.warning(t("ssh_monitoring_warning"))

    async def get_load_average(
        self, host: str, port: int = 22, username: Optional[str] = None
    ) -> Optional[Tuple[float, float, float]]:
        """Get load average from host via SSH"""
        try:
            # Use provided username or fallback to instance username
            ssh_username = username or self.username

            # Prepare connection options
            connect_options = {
                "host": host,
                "port": port,
                "username": ssh_username,
                "known_hosts": None,  # Disable host key checking for simplicity
                "connect_timeout": self.timeout,
            }

            # Add authentication
            if self.private_key_path:
                connect_options["client_keys"] = [self.private_key_path]
            if self.password:
                connect_options["password"] = self.password

            async with asyncssh.connect(**connect_options) as conn:
                # Get load average using cat /proc/loadavg
                result = await conn.run("cat /proc/loadavg", check=True)
                loadavg_output = result.stdout.strip()

                # Parse load average: "0.15 0.23 0.18 1/123 4567"
                parts = loadavg_output.split()
                if len(parts) >= 3:
                    load_1m = float(parts[0])
                    load_5m = float(parts[1])
                    load_15m = float(parts[2])

                    logging.debug(
                        t(
                            "ssh_load_average_debug",
                            host=host,
                            load_1m=load_1m,
                            load_5m=load_5m,
                            load_15m=load_15m,
                        )
                    )
                    return (load_1m, load_5m, load_15m)

        except asyncssh.Error as e:
            logging.debug(
                t("ssh_connection_failed", host=host, port=port, error=str(e))
            )
        except Exception as e:
            logging.debug(t("ssh_load_error", host=host, port=port, error=str(e)))

        return None

    async def monitor_nodes(self, nodes: List[NodeInfo]) -> None:
        """Monitor multiple nodes concurrently"""
        tasks = []

        for node in nodes:
            if (
                node.ssh_host and node.ssh_host.strip()
            ):  # Check that ssh_host is not empty
                task = self._monitor_single_node(node)
                tasks.append(task)

        if tasks:
            # Run all SSH connections concurrently
            logging.debug(t("ssh_monitoring_started", count=len(tasks)))
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logging.debug(t("ssh_monitoring_no_nodes"))

    async def _monitor_single_node(self, node: NodeInfo) -> None:
        """Monitor single node and update its load average"""
        try:
            load_avg = await self.get_load_average(
                node.ssh_host, node.ssh_port, node.ssh_user
            )
            if load_avg:
                (
                    node.load_average_1m,
                    node.load_average_5m,
                    node.load_average_15m,
                ) = load_avg
                node.ssh_available = True
                logging.debug(t("ssh_load_updated", node=node.name, load=load_avg))
            else:
                node.ssh_available = False
                logging.debug(t("ssh_monitoring_failed", node=node.name))
        except Exception as e:
            logging.debug(t("ssh_monitoring_exception", node=node.name, error=str(e)))
            node.ssh_available = False
