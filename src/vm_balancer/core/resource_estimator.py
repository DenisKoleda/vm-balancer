"""
Resource estimation utilities for VM Balancer
"""

import logging
from typing import Optional

from ..models.node import NodeInfo
from ..models.vm import VMInfo


class ResourceEstimator:
    """Handles resource estimation and compatibility checks"""

    def __init__(self, cpu_overload_threshold: float, memory_overload_threshold: float):
        """
        Initialize resource estimator

        Args:
            cpu_overload_threshold: CPU overload threshold
            memory_overload_threshold: Memory overload threshold
        """
        self.cpu_overload_threshold = cpu_overload_threshold
        self.memory_overload_threshold = memory_overload_threshold

    def estimate_post_migration_resources(
        self, node: NodeInfo, vm: VMInfo
    ) -> tuple[float, float]:
        """
        Estimate resource usage after VM migration

        Args:
            node: Target node
            vm: VM to migrate

        Returns:
            Tuple of (estimated_cpu_ratio, estimated_memory_percent)
        """
        estimated_cpu_ratio = (node.cpu_used + vm.cpu_cores) / node.cpu_total
        estimated_memory_percent = node.memory_usage_percent + (
            vm.memory_mb / node.memory_total_mb * 100
        )

        return estimated_cpu_ratio, estimated_memory_percent

    def can_node_accept_vm(
        self, node: NodeInfo, vm: VMInfo, source_node: Optional[NodeInfo] = None
    ) -> bool:
        """
        Check if node can accept the VM without becoming overloaded

        Args:
            node: Target node
            vm: VM to migrate
            source_node: Source node (for QEMU version compatibility)

        Returns:
            True if node can accept the VM
        """
        # Estimate resource usage after migration
        estimated_cpu_ratio, estimated_memory_percent = (
            self.estimate_post_migration_resources(node, vm)
        )

        # Check if resources are within acceptable limits
        cpu_ok = estimated_cpu_ratio < self.cpu_overload_threshold
        memory_ok = estimated_memory_percent < self.memory_overload_threshold

        # Check QEMU version compatibility
        qemu_ok = self._check_qemu_compatibility(node, source_node)

        logging.debug(
            f"Can {node.name} accept VM {vm.name}? Current: CPU"
            f" {node.cpu_allocation_ratio:.1f}:1, Memory"
            f" {node.memory_usage_percent:.1f}% | After: CPU"
            f" {estimated_cpu_ratio:.1f}:1, Memory {estimated_memory_percent:.1f}% |"
            f" CPU_ok={cpu_ok}, Memory_ok={memory_ok}, QEMU_ok={qemu_ok}"
        )

        return cpu_ok and memory_ok and qemu_ok

    def _check_qemu_compatibility(
        self, target_node: NodeInfo, source_node: Optional[NodeInfo]
    ) -> bool:
        """
        Check QEMU version compatibility between source and target nodes

        Args:
            target_node: Target node
            source_node: Source node

        Returns:
            True if QEMU versions are compatible
        """
        if not source_node:
            return True

        # If we don't have QEMU version info, assume compatible
        if not target_node.qemu_version or not source_node.qemu_version:
            self._log_missing_qemu_version(target_node, source_node)
            return True

        # Compare QEMU versions (simplified comparison)
        # In a real implementation, you'd use proper version comparison
        try:
            target_version = self._parse_qemu_version(target_node.qemu_version)
            source_version = self._parse_qemu_version(source_node.qemu_version)
            
            qemu_ok = target_version >= source_version
            
            if not qemu_ok:
                logging.warning(
                    f"QEMU version incompatible: source node {source_node.name} "
                    f"has QEMU {source_node.qemu_version}, target node {target_node.name} "
                    f"has QEMU {target_node.qemu_version}. Target QEMU version must be "
                    "equal or newer than source."
                )
            
            return qemu_ok
        except Exception as e:
            logging.debug(f"Error comparing QEMU versions: {e}")
            return True  # Assume compatible if we can't compare

    def _parse_qemu_version(self, version_str: str) -> tuple[int, ...]:
        """
        Parse QEMU version string into comparable tuple

        Args:
            version_str: QEMU version string

        Returns:
            Tuple of version numbers for comparison
        """
        # Simple version parsing - extract numbers from version string
        # This is a simplified implementation
        try:
            # Extract version numbers (e.g., "4.2.1" -> (4, 2, 1))
            version_parts = version_str.split('.')
            return tuple(int(part) for part in version_parts[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)

    def _log_missing_qemu_version(
        self, target_node: NodeInfo, source_node: NodeInfo
    ) -> None:
        """Log missing QEMU version information"""
        if not target_node.qemu_version and not source_node.qemu_version:
            logging.debug(
                f"QEMU version unknown for both source ({source_node.name}) and "
                f"target ({target_node.name}) nodes"
            )
        elif not target_node.qemu_version:
            logging.debug(f"QEMU version unknown for target node {target_node.name}")
        elif not source_node.qemu_version:
            logging.debug(f"QEMU version unknown for source node {source_node.name}")