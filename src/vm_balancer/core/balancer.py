"""
Core VM Balancer implementation
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..api.client import VMManagerAPI
from ..models.cluster import ClusterInfo
from ..models.node import NodeInfo
from ..models.vm import VMInfo
from ..monitoring.ssh import SSHMonitor
from ..notifications.telegram import TelegramNotifier
from ..utils.i18n import t


class VMBalancer:
    """Main balancer logic"""

    def __init__(
        self, config_path: str = ".env", dry_run: bool = False, verbose: bool = False
    ):
        """
        Initialize VM Balancer

        Args:
            config_path: Path to configuration file
            dry_run: If True, only simulate migrations
            verbose: Enable verbose logging
        """
        from ..utils.env import EnvConfig

        # Load configuration
        self.config = EnvConfig(config_path)
        self.dry_run = dry_run
        self.verbose = verbose

        # Configure logging
        log_level = (
            logging.DEBUG
            if verbose
            else getattr(logging, self.config.log_level.upper())
        )
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        # Initialize API client
        self.api = VMManagerAPI(
            host=self.config.vmmanager_host,
            username=self.config.vmmanager_username,
            password=self.config.vmmanager_password,
            verify_ssl=self.config.verify_ssl,
        )

        # Set configuration parameters
        self.balance_interval = self.config.balance_interval
        self.cluster_ids = self.config.cluster_ids
        self.cpu_overload_threshold = self.config.cpu_overload_threshold
        self.memory_overload_threshold = self.config.memory_overload_threshold
        self.cpu_target_threshold = self.config.cpu_target_threshold
        self.memory_target_threshold = self.config.memory_target_threshold
        self.excluded_source_nodes = set(self.config.exclude_source_nodes)
        self.excluded_target_nodes = set(self.config.exclude_target_nodes)
        self.max_migrations_per_cycle = self.config.max_migrations_per_cycle
        self.migration_timeout = self.config.migration_timeout

        # SSH configuration
        self.ssh_enabled = self.config.ssh_enabled
        self.ssh_hosts_mapping = self.config.ssh_hosts_mapping

        # Initialize optional components
        self.telegram_notifier = None
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            self.telegram_notifier = TelegramNotifier(
                bot_token=self.config.telegram_bot_token,
                chat_id=self.config.telegram_chat_id,
            )

        self.ssh_monitor = None
        if self.config.ssh_enabled:
            self.ssh_monitor = SSHMonitor(
                username=self.config.ssh_username,
                private_key_path=self.config.ssh_private_key_path,
                password=self.config.ssh_password,
                timeout=self.config.ssh_timeout,
                hosts_mapping=self.config.ssh_hosts_mapping,
            )

        # Internal state
        self.migration_history = {}  # Track recent migrations
        self.migration_blacklist = (
            {}
        )  # Track failed/timeout migrations to prevent retries

    def filter_clusters(self, clusters: List[ClusterInfo]) -> List[ClusterInfo]:
        """Filter clusters based on cluster_ids if specified"""
        if not self.cluster_ids:
            return clusters

        filtered = [cluster for cluster in clusters if cluster.id in self.cluster_ids]

        # Log which clusters are being processed
        cluster_names = [f"{c.name} (ID: {c.id})" for c in filtered]
        if cluster_names:
            logging.info(f"Processing specific clusters: {', '.join(cluster_names)}")
        else:
            logging.warning(
                f"No clusters found matching specified IDs: {self.cluster_ids}"
            )

        return filtered

    def find_overloaded_nodes(self, nodes: List[NodeInfo]) -> List[NodeInfo]:
        """Find nodes that are overloaded"""
        overloaded = []
        for node in nodes:
            # Skip excluded source nodes
            if (
                node.name in self.excluded_source_nodes
                or node.id in self.excluded_source_nodes
            ):
                logging.debug(f"Node {node.name} excluded from migration sources")
                continue

            # Use effective CPU load instead of just load score
            cpu_overloaded = node.effective_cpu_load > self.cpu_overload_threshold
            memory_overloaded = (
                node.memory_usage_percent > self.memory_overload_threshold
            )

            if not node.is_maintenance and (cpu_overloaded or memory_overloaded):
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
        """Find nodes that have capacity for more VMs"""
        underloaded = []
        for node in nodes:
            # Skip excluded target nodes
            if (
                node.name in self.excluded_target_nodes
                or node.id in self.excluded_target_nodes
            ):
                logging.debug(f"Node {node.name} excluded from migration targets")
                continue

            qemu_info = (
                f", QEMU={node.qemu_version}" if node.qemu_version else ", QEMU=unknown"
            )
            logging.debug(
                f"Checking node {node.name}: maintenance={node.is_maintenance},"
                f" vm_creation_allowed={node.vm_creation_allowed},"
                f" vm_count={node.vm_count}, vm_limit={node.vm_limit},"
                f" can_accept_vms={node.can_accept_vms},"
                f" CPU_ratio={node.cpu_allocation_ratio:.1f}:1"
                f" ({node.cpu_used}/{node.cpu_total}),"
                f" Memory={node.memory_usage_percent:.1f}%{qemu_info}"
            )

            # Check if node can accept VMs and has capacity (use effective CPU load)
            cpu_has_capacity = node.effective_cpu_load < self.cpu_target_threshold
            memory_has_capacity = (
                node.memory_usage_percent < self.memory_target_threshold
            )

            if node.can_accept_vms and cpu_has_capacity and memory_has_capacity:
                logging.debug(t("node_target_found", node_name=node.name))
                underloaded.append(node)
            else:
                reasons = []
                if not node.can_accept_vms:
                    if node.is_maintenance:
                        logging.debug(t("node_maintenance", node_name=node.name))
                        reasons.append("in maintenance")
                    if not node.vm_creation_allowed:
                        reasons.append("VM creation disabled")
                    if node.vm_limit > 0 and node.vm_count >= node.vm_limit:
                        reasons.append(
                            f"VM limit reached ({node.vm_count}/{node.vm_limit})"
                        )
                if not cpu_has_capacity:
                    reasons.append(
                        f"CPU load too high (score: {node.cpu_load_score:.1f})"
                    )
                if not memory_has_capacity:
                    reasons.append(
                        f"Memory too high ({node.memory_usage_percent:.1f}%)"
                    )

                if not reasons:  # If no specific reasons found, add generic message
                    reasons.append("unknown reason")

                logging.debug(f"Node {node.name} rejected: {', '.join(reasons)}")

        # Sort by available capacity (lowest load score first, then memory)
        underloaded.sort(key=lambda n: (n.cpu_load_score, n.memory_usage_percent))
        return underloaded

    def select_vm_for_migration(
        self, vms: List[VMInfo], source_node: NodeInfo
    ) -> Optional[VMInfo]:
        """Select best VM candidate for migration from overloaded node"""
        # Filter VMs that can be migrated and are on source node
        all_vms_on_node = [vm for vm in vms if vm.node_id == source_node.id]
        candidates = [vm for vm in all_vms_on_node if vm.can_migrate]

        logging.debug(
            f"Node {source_node.name}: {len(all_vms_on_node)} total VMs,"
            f" {len(candidates)} can migrate"
        )

        if not candidates:
            if all_vms_on_node:
                non_migratable_states = {}
                for vm in all_vms_on_node:
                    if not vm.can_migrate:
                        non_migratable_states[vm.state] = (
                            non_migratable_states.get(vm.state, 0) + 1
                        )
                logging.info(
                    f"Node {source_node.name}: {len(all_vms_on_node)} VMs present, but"
                    f" none can migrate. VM states: {dict(non_migratable_states)}"
                )
            else:
                logging.info(f"Node {source_node.name}: No VMs found on this node")
            return None

        # Exclude VMs that were recently migrated
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_candidates = [
            vm
            for vm in candidates
            if self.migration_history.get(vm.id, datetime.min) < recent_cutoff
        ]

        if not recent_candidates:
            logging.info(
                f"Node {source_node.name}: {len(candidates)} VMs can migrate, "
                "but all were recently migrated (within 1 hour)"
            )
            return None

        # Exclude VMs that are in blacklist (failed migrations within last 24 hours)
        blacklist_cutoff = datetime.now() - timedelta(hours=24)
        final_candidates = [
            vm
            for vm in recent_candidates
            if self.migration_blacklist.get(vm.id, datetime.min) < blacklist_cutoff
        ]

        if not final_candidates:
            blacklisted_count = len(recent_candidates) - len(final_candidates)
            logging.info(
                f"Node {source_node.name}: {len(recent_candidates)} VMs can migrate, "
                f"but {blacklisted_count} are blacklisted due to recent failures"
            )
            return None

        # Sort by resource usage (migrate smaller VMs first for easier balancing)
        final_candidates.sort(key=lambda vm: vm.cpu_cores + (vm.memory_mb / 1024))

        selected_vm = final_candidates[0]
        logging.debug(
            f"Node {source_node.name}: Selected VM {selected_vm.name} for migration "
            f"(CPU: {selected_vm.cpu_cores}, Memory: {selected_vm.memory_mb}MB)"
        )

        return selected_vm

    def can_node_accept_vm(self, node: NodeInfo, vm: VMInfo) -> bool:
        """Check if node can accept the VM without becoming overloaded"""
        # Estimate resource usage after migration
        estimated_cpu_ratio = (node.cpu_used + vm.cpu_cores) / node.cpu_total
        estimated_memory = node.memory_usage_percent + (
            vm.memory_mb / node.memory_total_mb * 100
        )

        cpu_ok = (
            estimated_cpu_ratio < self.cpu_overload_threshold
        )  # Use overload threshold for final check
        memory_ok = estimated_memory < self.memory_overload_threshold

        # Check QEMU version compatibility
        qemu_ok = True
        source_node = self.get_source_node_for_vm(vm)
        if source_node and node.qemu_version and source_node.qemu_version:
            qemu_ok = self.api.compare_qemu_versions(
                source_node.qemu_version, node.qemu_version
            )
            if not qemu_ok:
                logging.warning(
                    f"QEMU version incompatible for VM {vm.name}: source node"
                    f" {source_node.name} has QEMU {source_node.qemu_version}, target"
                    f" node {node.name} has QEMU {node.qemu_version}. Target QEMU"
                    " version must be equal or newer than source."
                )
        elif source_node:
            # Log when QEMU version information is missing
            if not node.qemu_version and not source_node.qemu_version:
                logging.debug(
                    f"QEMU version unknown for both source ({source_node.name}) and"
                    f" target ({node.name}) nodes"
                )
            elif not node.qemu_version:
                logging.debug(f"QEMU version unknown for target node {node.name}")
            elif not source_node.qemu_version:
                logging.debug(
                    f"QEMU version unknown for source node {source_node.name}"
                )

        logging.debug(
            f"Can {node.name} accept VM {vm.name}? Current: CPU"
            f" {node.cpu_allocation_ratio:.1f}:1, Memory"
            f" {node.memory_usage_percent:.1f}% | After: CPU"
            f" {estimated_cpu_ratio:.1f}:1, Memory {estimated_memory:.1f}% |"
            f" CPU_ok={cpu_ok}, Memory_ok={memory_ok}, QEMU_ok={qemu_ok}"
        )

        return cpu_ok and memory_ok and qemu_ok

    def get_source_node_for_vm(self, vm: VMInfo) -> Optional[NodeInfo]:
        """Find source node for given VM"""
        # This method needs access to current cluster nodes
        # We'll need to pass this information differently
        if hasattr(self, "_current_cluster_nodes"):
            for node in self._current_cluster_nodes:
                if node.id == vm.node_id:
                    return node
        return None

    def find_target_node(
        self, vm: VMInfo, underloaded_nodes: List[NodeInfo]
    ) -> Optional[NodeInfo]:
        """Find suitable target node for VM migration"""
        for node in underloaded_nodes:
            if self.can_node_accept_vm(node, vm):
                return node
        return None

    def balance_cluster(self, cluster: ClusterInfo) -> int:
        """Balance VMs in cluster, returns number of migrations performed"""
        logging.info(f"Starting balance check for cluster: {cluster.name}")

        # Update load averages via SSH if enabled
        if self.ssh_enabled and self.ssh_monitor:
            logging.debug("Updating node load averages via SSH...")
            try:
                # Run async SSH monitoring
                asyncio.run(self.update_nodes_load_average(cluster.nodes))
            except Exception as e:
                logging.warning(f"SSH monitoring failed: {e}, falling back to API data")

        # Store current cluster nodes for QEMU version checking
        self._current_cluster_nodes = cluster.nodes

        # Log threshold settings
        logging.debug(
            f"Thresholds - CPU overload: {self.cpu_overload_threshold} (load score), "
            f"Memory overload: {self.memory_overload_threshold}%, "
            f"CPU target: {self.cpu_target_threshold} (load score), "
            f"Memory target: {self.memory_target_threshold}%"
        )

        # Log migration settings
        logging.debug(
            "Migration settings - Max migrations per cycle:"
            f" {self.max_migrations_per_cycle}, Blacklist retention: 24 hours"
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
            node for node in cluster.nodes if not node.vm_creation_allowed
        ]
        if restricted_nodes:
            restricted_names = [node.name for node in restricted_nodes]
            logging.info(
                f"Nodes with VM creation disabled: {', '.join(restricted_names)}"
            )

        # Get current cluster state
        overloaded_nodes = self.find_overloaded_nodes(cluster.nodes)
        underloaded_nodes = self.find_underloaded_nodes(cluster.nodes)

        if not overloaded_nodes:
            logging.info(f"No overloaded nodes found in cluster {cluster.name}")
            return 0

        if not underloaded_nodes:
            logging.warning(f"No available target nodes in cluster {cluster.name}")
            return 0

        # Get VMs in cluster
        cluster_vms = self.api.get_cluster_vms(cluster.id)
        migrations_performed = 0

        # Try to migrate VMs up to the configured limit per iteration
        for source_node in overloaded_nodes:
            if (
                migrations_performed >= self.max_migrations_per_cycle
            ):  # Limit to max_migrations_per_cycle
                break

            logging.info(
                f"Node {source_node.name} is overloaded: CPU allocation"
                f" {source_node.cpu_allocation_ratio:.1f}:1"
                f" ({source_node.cpu_used}/{source_node.cpu_total}), CPU load score"
                f" {source_node.cpu_load_score:.1f}, Memory"
                f" {source_node.memory_usage_percent:.1f}%"
            )

            # Select VM to migrate
            vm_to_migrate = self.select_vm_for_migration(cluster_vms, source_node)
            if not vm_to_migrate:
                logging.info(
                    f"No suitable VM found for migration from {source_node.name}"
                )
                continue

            # Find target node
            target_node = self.find_target_node(vm_to_migrate, underloaded_nodes)
            if not target_node:
                logging.info(
                    f"No suitable target node found for VM {vm_to_migrate.name}"
                )
                continue

            # Perform migration
            logging.info(
                f"{'[DRY RUN] Would migrate' if self.dry_run else 'Migrating'} VM"
                f" {vm_to_migrate.name} from {source_node.name} to {target_node.name}"
            )

            # Notify migration start
            self.telegram_notifier.notify_migration_start(
                vm_to_migrate.name, source_node.name, target_node.name
            )

            if self.dry_run:
                # In dry run mode, just log what would be done
                logging.info(
                    f"[DRY RUN] VM {vm_to_migrate.name} migration simulated"
                    " successfully"
                )
                self.telegram_notifier.notify_migration_success(
                    vm_to_migrate.name, source_node.name, target_node.name, 0
                )
                migrations_performed += 1

                # Update node info for simulation
                source_node.vm_count -= 1
                target_node.vm_count += 1
            else:
                # Real migration - track start time for duration calculation
                migration_start_time = time.time()

                if self.api.migrate_vm(
                    vm_to_migrate.id, target_node.id, self.migration_timeout
                ):
                    migration_duration = time.time() - migration_start_time
                    logging.info(f"Successfully migrated VM {vm_to_migrate.name}")
                    self.migration_history[vm_to_migrate.id] = datetime.now()
                    migrations_performed += 1

                    # Notify successful migration
                    self.telegram_notifier.notify_migration_success(
                        vm_to_migrate.name,
                        source_node.name,
                        target_node.name,
                        migration_duration,
                    )

                    # Update node info after migration
                    source_node.vm_count -= 1
                    target_node.vm_count += 1

                    # Remove target node from underloaded list if it's getting full
                    if not self.can_node_accept_vm(target_node, vm_to_migrate):
                        underloaded_nodes.remove(target_node)
                else:
                    logging.error(f"Failed to migrate VM {vm_to_migrate.name}")
                    # Add to blacklist to prevent retry attempts for 24 hours
                    self.migration_blacklist[vm_to_migrate.id] = datetime.now()
                    logging.debug(
                        f"VM {vm_to_migrate.name} added to migration blacklist"
                    )

                    # Notify failed migration
                    self.telegram_notifier.notify_migration_failure(
                        vm_to_migrate.name,
                        source_node.name,
                        target_node.name,
                        "Migration failed",
                    )

        # Clean up cluster nodes reference
        self._current_cluster_nodes = None

        return migrations_performed

    def run_balance_cycle(self) -> None:
        """Run one complete balance cycle for all clusters"""
        mode_text = "[DRY RUN] " if self.dry_run else ""
        logging.info(f"{mode_text}Starting balance cycle")

        # Authenticate with VMManager first
        if not self.api.authenticate():
            logging.error("Failed to authenticate with VMManager API")
            return

        # Check if VMManager is ready
        if not self.api.check_manager_state():
            logging.error("VMManager API is not accessible")
            return

        # Get all clusters
        all_clusters = self.api.get_clusters()
        if not all_clusters:
            logging.warning("No clusters found")
            return

        # Filter clusters if specific cluster IDs are specified
        clusters = self.filter_clusters(all_clusters)
        if not clusters:
            logging.warning("No clusters to process after filtering")
            return

        # Setup SSH monitoring for all cluster nodes
        if self.ssh_enabled and self.ssh_monitor:
            all_nodes = []
            for cluster in clusters:
                all_nodes.extend(cluster.nodes)
            # SSH hosts mapping could be stored as an instance variable or passed from config
            self.setup_ssh_monitoring(all_nodes, self.ssh_hosts_mapping)

        # Notify balance cycle start
        self.telegram_notifier.notify_balance_cycle_start(len(clusters), self.dry_run)

        total_migrations = 0
        for cluster in clusters:
            try:
                migrations = self.balance_cluster(cluster)
                total_migrations += migrations
            except Exception as e:
                logging.error(f"Error balancing cluster {cluster.name}: {e}")

        logging.info(
            f"{mode_text}Balance cycle completed. Total migrations: {total_migrations}"
        )

        # Notify balance cycle completion
        self.telegram_notifier.notify_balance_cycle_complete(
            total_migrations, self.dry_run
        )

    def setup_ssh_monitoring(
        self, nodes: List[NodeInfo], ssh_hosts_mapping: Optional[Dict[str, str]] = None
    ) -> None:
        """Setup SSH monitoring for nodes"""
        if not self.ssh_enabled or not self.ssh_monitor:
            return

        nodes_configured = 0
        for node in nodes:
            # Priority: API data > manual mapping > node name fallback
            if node.ssh_host:  # Already has SSH host from API
                nodes_configured += 1
                logging.debug(
                    f"SSH monitoring for node {node.name}:"
                    f" host={node.ssh_host}:{node.ssh_port}, user={node.ssh_user} (from"
                    " API)"
                )
            elif ssh_hosts_mapping and node.name in ssh_hosts_mapping:
                node.ssh_host = ssh_hosts_mapping[node.name]
                nodes_configured += 1
                logging.debug(
                    f"SSH monitoring for node {node.name}: host={node.ssh_host} (from"
                    " name mapping)"
                )
            elif ssh_hosts_mapping and node.id in ssh_hosts_mapping:
                node.ssh_host = ssh_hosts_mapping[node.id]
                nodes_configured += 1
                logging.debug(
                    f"SSH monitoring for node {node.name}: host={node.ssh_host} (from"
                    " ID mapping)"
                )
            else:
                # Try to use node name as hostname (fallback)
                node.ssh_host = node.name
                logging.debug(
                    f"SSH monitoring for node {node.name}:"
                    f" host={node.ssh_host} (fallback to node name)"
                )

        if nodes_configured > 0:
            logging.info(
                f"SSH monitoring configured for {nodes_configured}/{len(nodes)} nodes"
            )

    async def update_nodes_load_average(self, nodes: List[NodeInfo]) -> None:
        """Update load average for all nodes via SSH"""
        if not self.ssh_enabled or not self.ssh_monitor:
            return

        nodes_with_ssh = [
            node for node in nodes if node.ssh_host and node.ssh_host.strip()
        ]
        if not nodes_with_ssh:
            logging.debug("No nodes configured for SSH monitoring")
            return

        logging.info(f"Updating load average for {len(nodes_with_ssh)} nodes via SSH")
        await self.ssh_monitor.monitor_nodes(nodes_with_ssh)

        # Log results
        successful_ssh = 0
        for node in nodes_with_ssh:
            if node.ssh_available:
                successful_ssh += 1
                logging.info(
                    f"Node {node.name}: SSH load_avg={node.load_average_1m:.2f}, "
                    f"effective_load={node.effective_cpu_load:.2f}, "
                    f"api_allocation={node.cpu_allocation_ratio:.2f}"
                )
            else:
                logging.debug(
                    f"Node {node.name}: SSH monitoring failed, using API data"
                    f" (allocation={node.cpu_allocation_ratio:.2f})"
                )

        if successful_ssh > 0:
            logging.info(
                "SSH monitoring successful for"
                f" {successful_ssh}/{len(nodes_with_ssh)} nodes"
            )
        else:
            logging.warning(
                "SSH monitoring failed for all nodes, falling back to API data"
            )

    async def run_once(self) -> None:
        """Run one balancing cycle"""
        try:
            logging.info(t("balancer_starting"))

            # Authenticate with VMManager first
            if not self.api.authenticate():
                logging.error("Failed to authenticate with VMManager API")
                return

            # Get all clusters
            clusters = self.api.get_clusters()
            filtered_clusters = self.filter_clusters(clusters)

            if not filtered_clusters:
                logging.warning(t("balancer_no_clusters"))
                return

            logging.info(t("balancer_cycle_start", count=len(filtered_clusters)))

            for cluster in filtered_clusters:
                logging.info(f"Processing cluster: {cluster.name} (ID: {cluster.id})")

                # Get cluster nodes and VMs
                nodes = self.api.get_cluster_nodes(cluster.id)
                vms = self.api.get_cluster_vms(cluster.id)

                if not nodes:
                    logging.warning(f"No nodes found in cluster {cluster.name}")
                    continue

                if not vms:
                    logging.info(f"No VMs found in cluster {cluster.name}")
                    continue

                # Setup SSH monitoring for nodes if enabled
                self.setup_ssh_monitoring(nodes)

                # Update nodes with load average via SSH
                await self.update_nodes_load_average(nodes)

                # Check if balancing is needed
                overloaded_nodes = self.find_overloaded_nodes(nodes)

                if not overloaded_nodes:
                    logging.info(f"Cluster {cluster.name}: {t('balancer_no_clusters')}")
                    continue

                logging.info(
                    f"Cluster {cluster.name}: Found {len(overloaded_nodes)} overloaded"
                    " node(s)"
                )

                # Process migrations for this cluster
                migrations_performed = 0

                for source_node in overloaded_nodes:
                    if migrations_performed >= self.max_migrations_per_cycle:
                        logging.info(
                            "Maximum migrations per cycle reached"
                            f" ({self.max_migrations_per_cycle})"
                        )
                        break

                    # Get VMs on this node
                    node_vms = [vm for vm in vms if vm.node_id == source_node.id]

                    if not node_vms:
                        logging.debug(
                            f"No VMs found on overloaded node {source_node.name}"
                        )
                        continue

                    # Select VM to migrate
                    vm_to_migrate = self.select_vm_for_migration(node_vms, source_node)

                    if not vm_to_migrate:
                        logging.debug(
                            "No suitable VM found for migration from node"
                            f" {source_node.name}"
                        )
                        continue

                    # Find target node
                    underloaded_nodes = self.find_underloaded_nodes(nodes)
                    target_node = self.find_target_node(
                        vm_to_migrate, underloaded_nodes
                    )

                    if not target_node:
                        logging.warning(t("node_no_target", vm_name=vm_to_migrate.name))
                        continue

                    # Perform migration
                    if await self.migrate_vm(vm_to_migrate, source_node, target_node):
                        migrations_performed += 1

                logging.info(
                    f"Cluster {cluster.name}: Completed"
                    f" {migrations_performed} migration(s)"
                )

            # Send cycle completion notification
            if self.telegram_notifier:
                await self.telegram_notifier.send_cycle_completed(
                    len(filtered_clusters)
                )

            logging.info(t("balancer_cycle_complete"))

        except Exception as e:
            logging.error(t("error_cluster_load", cluster_id="cycle", error=str(e)))
            if self.telegram_notifier:
                await self.telegram_notifier.send_error_notification(str(e))
            raise

    async def run(self) -> None:
        """Run continuous balancing loop"""
        logging.info(
            "Starting VM Balancer in continuous mode (interval:"
            f" {self.balance_interval}s)"
        )

        while True:
            try:
                await self.run_once()

                logging.info(
                    f"Waiting {self.balance_interval} seconds until next cycle..."
                )
                await asyncio.sleep(self.balance_interval)

            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, stopping...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                logging.info(f"Waiting {self.balance_interval} seconds before retry...")
                await asyncio.sleep(self.balance_interval)

    async def migrate_vm(
        self, vm: VMInfo, source_node: NodeInfo, target_node: NodeInfo
    ) -> bool:
        """Migrate a VM from source to target node"""
        if self.dry_run:
            logging.info(
                t(
                    "migration_dry_run",
                    vm_name=vm.name,
                    source_node=source_node.name,
                    target_node=target_node.name,
                )
            )
        else:
            logging.info(
                t(
                    "migration_start",
                    vm_name=vm.name,
                    source_node=source_node.name,
                    target_node=target_node.name,
                )
            )

        # Notify migration start
        if self.telegram_notifier:
            await self.telegram_notifier.notify_migration_start(
                vm.name, source_node.name, target_node.name
            )

        if self.dry_run:
            # In dry run mode, just log what would be done
            logging.info(t("migration_success", vm_name=vm.name))
            if self.telegram_notifier:
                await self.telegram_notifier.notify_migration_success(
                    vm.name, source_node.name, target_node.name, 0
                )

            # Update node info for simulation
            source_node.vm_count -= 1
            target_node.vm_count += 1
            return True
        else:
            # Real migration - track start time for duration calculation
            migration_start_time = time.time()

            if self.api.migrate_vm(vm.id, target_node.id, self.migration_timeout):
                migration_duration = time.time() - migration_start_time
                logging.info(t("migration_success", vm_name=vm.name))
                self.migration_history[vm.id] = datetime.now()

                # Notify successful migration
                if self.telegram_notifier:
                    await self.telegram_notifier.notify_migration_success(
                        vm.name, source_node.name, target_node.name, migration_duration
                    )

                # Update node info after migration
                source_node.vm_count -= 1
                target_node.vm_count += 1
                return True
            else:
                logging.error(
                    t("migration_failed", vm_name=vm.name, error="Migration failed")
                )
                # Add to blacklist to prevent retry attempts for 24 hours
                self.migration_blacklist[vm.id] = datetime.now()
                logging.debug(f"VM {vm.name} added to migration blacklist")

                # Notify failed migration
                if self.telegram_notifier:
                    await self.telegram_notifier.notify_migration_failure(
                        vm.name, source_node.name, target_node.name, "Migration failed"
                    )
                return False
