"""
Node data model for VM Balancer
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NodeInfo:
    """Information about cluster node"""

    id: str
    name: str
    cpu_total: int
    cpu_used: int
    memory_total_mb: int
    memory_used_mb: int
    vm_count: int
    is_maintenance: bool = False
    vm_creation_allowed: bool = True  # Check if VM creation is allowed on this node
    vm_limit: int = 0  # VM limit for this node (0 = no limit)
    qemu_version: str = ""  # QEMU version on this node
    # SSH monitoring fields
    ssh_host: Optional[str] = None  # SSH hostname or IP
    ssh_port: int = 22  # SSH port
    ssh_user: Optional[str] = None  # SSH username from API
    load_average_1m: Optional[float] = None  # 1-minute load average from SSH
    load_average_5m: Optional[float] = None  # 5-minute load average from SSH
    load_average_15m: Optional[float] = None  # 15-minute load average from SSH
    ssh_available: bool = False  # Whether SSH monitoring is available

    @property
    def cpu_usage_percent(self) -> float:
        """Calculate CPU usage percentage based on vCPU allocation"""
        # cpu_used is allocated vCPUs to VMs, cpu_total is physical cores
        # We calculate allocation ratio, not actual CPU usage
        return (self.cpu_used / self.cpu_total * 100) if self.cpu_total > 0 else 0.0

    @property
    def cpu_allocation_ratio(self) -> float:
        """Calculate vCPU to physical CPU allocation ratio"""
        return (self.cpu_used / self.cpu_total) if self.cpu_total > 0 else 0.0

    @property
    def cpu_load_score(self) -> float:
        """Calculate a more sophisticated CPU load score combining allocation ratio and VM density"""
        if self.cpu_total <= 0:
            return 0.0

        # Prioritize SSH load average if available
        if self.ssh_available and self.load_average_1m is not None:
            # Use 1-minute load average normalized by CPU count
            ssh_load_score = self.load_average_1m / self.cpu_total

            # Add VM density factor
            from ..core.constants import VM_DENSITY_FACTOR_CAP, SSH_VM_DENSITY_FACTOR_WEIGHT
            
            vm_density_factor = min(self.vm_count / max(self.cpu_total, 1), VM_DENSITY_FACTOR_CAP)

            return ssh_load_score + (vm_density_factor * SSH_VM_DENSITY_FACTOR_WEIGHT)

        # Fallback to allocation ratio
        allocation_ratio = self.cpu_allocation_ratio

        # VM density factor (more VMs = higher complexity/overhead)
        from ..core.constants import VM_DENSITY_FACTOR_CAP, VM_DENSITY_FACTOR_WEIGHT
        
        vm_density_factor = min(
            self.vm_count / max(self.cpu_total, 1), VM_DENSITY_FACTOR_CAP
        )

        # Combined score: allocation ratio + density penalty
        load_score = allocation_ratio + (vm_density_factor * VM_DENSITY_FACTOR_WEIGHT)

        return load_score

    @property
    def effective_cpu_load(self) -> float:
        """Get effective CPU load - prioritize SSH load average, fallback to allocation ratio"""
        if self.ssh_available and self.load_average_1m is not None:
            return self.load_average_1m / self.cpu_total if self.cpu_total > 0 else 0.0
        return self.cpu_allocation_ratio

    @property
    def memory_usage_percent(self) -> float:
        """Calculate memory usage percentage"""
        return (
            (self.memory_used_mb / self.memory_total_mb * 100)
            if self.memory_total_mb > 0
            else 0.0
        )

    @property
    def is_overloaded(self) -> bool:
        """Check if node is overloaded based on thresholds"""
        # Note: This will be updated by the balancer with actual thresholds
        # For now using default values, but the balancer will override this check
        from ..core.constants import DEFAULT_CPU_OVERLOAD_THRESHOLD, DEFAULT_MEMORY_OVERLOAD_THRESHOLD
        
        cpu_overloaded = self.cpu_allocation_ratio > DEFAULT_CPU_OVERLOAD_THRESHOLD
        memory_overloaded = self.memory_usage_percent > DEFAULT_MEMORY_OVERLOAD_THRESHOLD
        return cpu_overloaded or memory_overloaded

    @property
    def can_accept_vms(self) -> bool:
        """Check if node can accept new VMs (not in maintenance, VM creation allowed, and under VM limit)"""
        vm_limit_ok = (
            self.vm_limit <= 0 or self.vm_count < self.vm_limit
        )  # -1 or 0 means no limit
        return not self.is_maintenance and self.vm_creation_allowed and vm_limit_ok

    def __str__(self) -> str:
        return f"Node {self.name} (ID: {self.id})"

    def __repr__(self) -> str:
        return (
            f"NodeInfo(id='{self.id}', name='{self.name}', "
            f"cpu_total={self.cpu_total}, cpu_used={self.cpu_used}, "
            f"memory_total_mb={self.memory_total_mb}, "
            f"memory_used_mb={self.memory_used_mb}, vm_count={self.vm_count})"
        )
