"""
Node analyzer for VM Balancer
"""

import logging
from typing import List, Set

from ..models.node import NodeInfo
from ..utils.i18n import t


class NodeAnalyzer:
    """Handles node analysis and filtering logic"""

    def __init__(
        self,
        cpu_overload_threshold: float,
        memory_overload_threshold: float,
        cpu_target_threshold: float,
        memory_target_threshold: float,
        excluded_source_nodes: Set[str],
        excluded_target_nodes: Set[str],
    ):
        """
        Initialize node analyzer

        Args:
            cpu_overload_threshold: CPU overload threshold
            memory_overload_threshold: Memory overload threshold
            cpu_target_threshold: CPU target threshold
            memory_target_threshold: Memory target threshold
            excluded_source_nodes: Set of excluded source nodes
            excluded_target_nodes: Set of excluded target nodes
        """
        self.cpu_overload_threshold = cpu_overload_threshold
        self.memory_overload_threshold = memory_overload_threshold
        self.cpu_target_threshold = cpu_target_threshold
        self.memory_target_threshold = memory_target_threshold
        self.excluded_source_nodes = excluded_source_nodes
        self.excluded_target_nodes = excluded_target_nodes

    def find_overloaded_nodes(self, nodes: List[NodeInfo]) -> List[NodeInfo]:
        """
        Find nodes that are overloaded

        Args:
            nodes: List of nodes to analyze

        Returns:
            List of overloaded nodes, sorted by load
        """
        overloaded = []
        
        for node in nodes:
            # Skip excluded source nodes
            if self._is_excluded_source_node(node):
                logging.debug(f"Node {node.name} excluded from migration sources")
                continue

            # Check if node is overloaded
            if self._is_node_overloaded(node):
                logging.info(
                    t(
                        "node_overloaded",
                        node_name=node.name,
                        cpu_load=node.effective_cpu_load,
                        memory_usage=node.memory_usage_percent,
                    )
                )
                overloaded.append(node)

        # Sort by combined load score (most loaded first)
        overloaded.sort(
            key=lambda n: n.cpu_load_score + (n.memory_usage_percent / 100),
            reverse=True,
        )
        
        return overloaded

    def find_underloaded_nodes(self, nodes: List[NodeInfo]) -> List[NodeInfo]:
        """
        Find nodes that have capacity for more VMs

        Args:
            nodes: List of nodes to analyze

        Returns:
            List of underloaded nodes, sorted by available capacity
        """
        underloaded = []
        
        for node in nodes:
            # Skip excluded target nodes
            if self._is_excluded_target_node(node):
                logging.debug(f"Node {node.name} excluded from migration targets")
                continue

            self._log_node_details(node)

            # Check if node has capacity
            if self._has_node_capacity(node):
                logging.debug(t("node_target_found", node_name=node.name))
                underloaded.append(node)
            else:
                self._log_node_rejection_reasons(node)

        # Sort by available capacity (lowest load score first, then memory)
        underloaded.sort(key=lambda n: (n.cpu_load_score, n.memory_usage_percent))
        
        return underloaded

    def log_cluster_analysis(self, nodes: List[NodeInfo]) -> None:
        """
        Log cluster analysis information

        Args:
            nodes: List of nodes to analyze
        """
        # Log migration settings
        logging.debug(
            f"Thresholds - CPU overload: {self.cpu_overload_threshold} (load score), "
            f"Memory overload: {self.memory_overload_threshold}%, "
            f"CPU target: {self.cpu_target_threshold} (load score), "
            f"Memory target: {self.memory_target_threshold}%"
        )

        # Log excluded nodes
        if self.excluded_source_nodes:
            logging.info(
                f"Excluded migration sources: {', '.join(self.excluded_source_nodes)}"
            )
        if self.excluded_target_nodes:
            logging.info(
                f"Excluded migration targets: {', '.join(self.excluded_target_nodes)}"
            )

        # Log nodes with restrictions
        restricted_nodes = [
            node for node in nodes if not node.vm_creation_allowed
        ]
        if restricted_nodes:
            restricted_names = [node.name for node in restricted_nodes]
            logging.info(
                f"Nodes with VM creation disabled: {', '.join(restricted_names)}"
            )

    def _is_excluded_source_node(self, node: NodeInfo) -> bool:
        """Check if node is excluded from being a migration source"""
        return (
            node.name in self.excluded_source_nodes
            or node.id in self.excluded_source_nodes
        )

    def _is_excluded_target_node(self, node: NodeInfo) -> bool:
        """Check if node is excluded from being a migration target"""
        return (
            node.name in self.excluded_target_nodes
            or node.id in self.excluded_target_nodes
        )

    def _is_node_overloaded(self, node: NodeInfo) -> bool:
        """Check if node is overloaded"""
        # Use effective CPU load instead of just load score
        cpu_overloaded = node.effective_cpu_load > self.cpu_overload_threshold
        memory_overloaded = node.memory_usage_percent > self.memory_overload_threshold

        return not node.is_maintenance and (cpu_overloaded or memory_overloaded)

    def _has_node_capacity(self, node: NodeInfo) -> bool:
        """Check if node has capacity for more VMs"""
        # Check if node can accept VMs and has capacity (use effective CPU load)
        cpu_has_capacity = node.effective_cpu_load < self.cpu_target_threshold
        memory_has_capacity = node.memory_usage_percent < self.memory_target_threshold

        return node.can_accept_vms and cpu_has_capacity and memory_has_capacity

    def _log_node_details(self, node: NodeInfo) -> None:
        """Log detailed node information"""
        qemu_info = (
            f", QEMU={node.qemu_version}" if node.qemu_version else ", QEMU=unknown"
        )
        logging.debug(
            f"Checking node {node.name}: maintenance={node.is_maintenance}, "
            f"vm_creation_allowed={node.vm_creation_allowed}, "
            f"vm_count={node.vm_count}, vm_limit={node.vm_limit}, "
            f"can_accept_vms={node.can_accept_vms}, "
            f"CPU_ratio={node.cpu_allocation_ratio:.1f}:1 "
            f"({node.cpu_used}/{node.cpu_total}), "
            f"Memory={node.memory_usage_percent:.1f}%{qemu_info}"
        )

    def _log_node_rejection_reasons(self, node: NodeInfo) -> None:
        """Log reasons why node was rejected as target"""
        reasons = []
        
        if not node.can_accept_vms:
            if node.is_maintenance:
                logging.debug(t("node_maintenance", node_name=node.name))
                reasons.append("in maintenance")
            if not node.vm_creation_allowed:
                reasons.append("VM creation disabled")
            if node.vm_limit > 0 and node.vm_count >= node.vm_limit:
                reasons.append(f"VM limit reached ({node.vm_count}/{node.vm_limit})")
        
        if node.effective_cpu_load >= self.cpu_target_threshold:
            reasons.append(f"CPU load too high (score: {node.cpu_load_score:.1f})")
        
        if node.memory_usage_percent >= self.memory_target_threshold:
            reasons.append(f"Memory too high ({node.memory_usage_percent:.1f}%)")

        if not reasons:  # If no specific reasons found, add generic message
            reasons.append("unknown reason")

        logging.debug(f"Node {node.name} rejected: {', '.join(reasons)}")