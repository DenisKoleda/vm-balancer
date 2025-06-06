"""
Cluster data model for VM Balancer
"""

from dataclasses import dataclass
from typing import List

from .node import NodeInfo


@dataclass
class ClusterInfo:
    """Information about cluster"""

    id: str
    name: str
    nodes: List[NodeInfo]
    balancer_enabled: bool = False

    def __str__(self) -> str:
        return f"Cluster {self.name} (ID: {self.id}) with {len(self.nodes)} nodes"

    def __repr__(self) -> str:
        return (
            f"ClusterInfo(id='{self.id}', name='{self.name}', "
            f"nodes={len(self.nodes)} nodes, "
            f"balancer_enabled={self.balancer_enabled})"
        )

    @property
    def active_nodes(self) -> List[NodeInfo]:
        """Get list of active (non-maintenance) nodes"""
        return [node for node in self.nodes if not node.is_maintenance]

    @property
    def available_nodes(self) -> List[NodeInfo]:
        """Get list of nodes that can accept VMs"""
        return [node for node in self.nodes if node.can_accept_vms]

    @property
    def total_cpu_cores(self) -> int:
        """Get total CPU cores across all nodes"""
        return sum(node.cpu_total for node in self.nodes)

    @property
    def total_memory_mb(self) -> int:
        """Get total memory across all nodes"""
        return sum(node.memory_total_mb for node in self.nodes)

    @property
    def total_vms(self) -> int:
        """Get total number of VMs across all nodes"""
        return sum(node.vm_count for node in self.nodes)
