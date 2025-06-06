"""
Data models for VM Balancer
"""

from dataclasses import dataclass


@dataclass
class VMInfo:
    """Information about virtual machine"""

    id: str
    name: str
    node_id: str
    cpu_cores: int
    memory_mb: int
    state: str
    can_migrate: bool = True

    def __str__(self) -> str:
        return f"VM {self.name} (ID: {self.id}) on node {self.node_id}"

    def __repr__(self) -> str:
        return (
            f"VMInfo(id='{self.id}', name='{self.name}', "
            f"node_id='{self.node_id}', cpu_cores={self.cpu_cores}, "
            f"memory_mb={self.memory_mb}, state='{self.state}', "
            f"can_migrate={self.can_migrate})"
        )
