"""
VM Balancer - Автоматическая балансировка виртуальных машин между узлами кластера VMManager 6

This package provides automated load balancing for virtual machines across cluster nodes
in VMManager 6 environment.
"""

__version__ = "2.0.0"
__author__ = "VMBalancer Team"
__email__ = "support@vmbalancer.com"

from .api.client import VMManagerAPI
from .core.balancer import VMBalancer
from .models.cluster import ClusterInfo
from .models.node import NodeInfo
from .models.vm import VMInfo
from .monitoring.ssh import SSHMonitor
from .notifications.telegram import TelegramNotifier

__all__ = [
    "VMBalancer",
    "VMManagerAPI",
    "ClusterInfo",
    "NodeInfo",
    "VMInfo",
    "TelegramNotifier",
    "SSHMonitor",
]
