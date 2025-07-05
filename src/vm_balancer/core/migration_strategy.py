"""
Migration strategy for VM Balancer
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..models.node import NodeInfo
from ..models.vm import VMInfo
from ..utils.i18n import t
from .constants import (
    MIGRATION_BLACKLIST_RETENTION_HOURS,
    MIGRATION_HISTORY_RETENTION_HOURS,
)
from .resource_estimator import ResourceEstimator


class MigrationStrategy:
    """Handles VM migration strategy and selection logic"""

    def __init__(
        self,
        resource_estimator: ResourceEstimator,
        migration_history: Dict[str, datetime],
        migration_blacklist: Dict[str, datetime],
    ):
        """
        Initialize migration strategy

        Args:
            resource_estimator: Resource estimator instance
            migration_history: Dictionary tracking recent migrations
            migration_blacklist: Dictionary tracking failed migrations
        """
        self.resource_estimator = resource_estimator
        self.migration_history = migration_history
        self.migration_blacklist = migration_blacklist

    def select_vm_for_migration(
        self, vms: List[VMInfo], source_node: NodeInfo
    ) -> Optional[VMInfo]:
        """
        Select best VM candidate for migration from overloaded node

        Args:
            vms: List of all VMs
            source_node: Source node to migrate from

        Returns:
            Selected VM or None if no suitable VM found
        """
        # Filter VMs that are on the source node
        all_vms_on_node = [vm for vm in vms if vm.node_id == source_node.id]
        candidates = [vm for vm in all_vms_on_node if vm.can_migrate]

        logging.debug(
            f"Node {source_node.name}: {len(all_vms_on_node)} total VMs, "
            f"{len(candidates)} can migrate"
        )

        if not candidates:
            self._log_no_candidates_reason(all_vms_on_node, source_node)
            return None

        # Filter out recently migrated VMs
        candidates = self._filter_recently_migrated_vms(candidates, source_node)
        if not candidates:
            return None

        # Filter out blacklisted VMs
        candidates = self._filter_blacklisted_vms(candidates, source_node)
        if not candidates:
            return None

        # Sort by resource usage (migrate smaller VMs first for easier balancing)
        candidates.sort(key=lambda vm: vm.cpu_cores + (vm.memory_mb / 1024))

        selected_vm = candidates[0]
        logging.debug(
            f"Node {source_node.name}: Selected VM {selected_vm.name} for migration "
            f"(CPU: {selected_vm.cpu_cores}, Memory: {selected_vm.memory_mb}MB)"
        )

        return selected_vm

    def find_target_node(
        self, vm: VMInfo, underloaded_nodes: List[NodeInfo], source_node: NodeInfo
    ) -> Optional[NodeInfo]:
        """
        Find suitable target node for VM migration

        Args:
            vm: VM to migrate
            underloaded_nodes: List of potential target nodes
            source_node: Source node (for compatibility checks)

        Returns:
            Target node or None if no suitable target found
        """
        for node in underloaded_nodes:
            if self.resource_estimator.can_node_accept_vm(node, vm, source_node):
                return node
        return None

    def record_migration_start(self, vm_id: str) -> None:
        """
        Record that a migration has started for a VM

        Args:
            vm_id: VM ID
        """
        self.migration_history[vm_id] = datetime.now()

    def record_migration_failure(self, vm_id: str) -> None:
        """
        Record that a migration has failed for a VM

        Args:
            vm_id: VM ID
        """
        self.migration_blacklist[vm_id] = datetime.now()

    def _filter_recently_migrated_vms(
        self, candidates: List[VMInfo], source_node: NodeInfo
    ) -> List[VMInfo]:
        """Filter out VMs that were recently migrated"""
        recent_cutoff = datetime.now() - timedelta(hours=MIGRATION_HISTORY_RETENTION_HOURS)
        recent_candidates = [
            vm
            for vm in candidates
            if self.migration_history.get(vm.id, datetime.min) < recent_cutoff
        ]

        if not recent_candidates:
            logging.info(
                f"Node {source_node.name}: {len(candidates)} VMs can migrate, "
                f"but all were recently migrated (within {MIGRATION_HISTORY_RETENTION_HOURS} hour(s))"
            )
            return []

        return recent_candidates

    def _filter_blacklisted_vms(
        self, candidates: List[VMInfo], source_node: NodeInfo
    ) -> List[VMInfo]:
        """Filter out VMs that are blacklisted due to recent failures"""
        blacklist_cutoff = datetime.now() - timedelta(hours=MIGRATION_BLACKLIST_RETENTION_HOURS)
        final_candidates = [
            vm
            for vm in candidates
            if self.migration_blacklist.get(vm.id, datetime.min) < blacklist_cutoff
        ]

        if not final_candidates:
            blacklisted_count = len(candidates) - len(final_candidates)
            logging.info(
                f"Node {source_node.name}: {len(candidates)} VMs can migrate, "
                f"but {blacklisted_count} are blacklisted due to recent failures"
            )
            return []

        return final_candidates

    def _log_no_candidates_reason(
        self, all_vms_on_node: List[VMInfo], source_node: NodeInfo
    ) -> None:
        """Log why no migration candidates are available"""
        if all_vms_on_node:
            non_migratable_states = {}
            for vm in all_vms_on_node:
                if not vm.can_migrate:
                    non_migratable_states[vm.state] = (
                        non_migratable_states.get(vm.state, 0) + 1
                    )
            logging.info(
                f"Node {source_node.name}: {len(all_vms_on_node)} VMs present, but "
                f"none can migrate. VM states: {dict(non_migratable_states)}"
            )
        else:
            logging.info(f"Node {source_node.name}: No VMs found on this node")