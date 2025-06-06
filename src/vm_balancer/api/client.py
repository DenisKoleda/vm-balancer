"""
VMManager 6 API client
"""

import logging
import time
from typing import Dict, List, Tuple

import requests

from ..models.cluster import ClusterInfo
from ..models.node import NodeInfo
from ..models.vm import VMInfo


class VMManagerAPI:
    """VMManager 6 API client"""

    def __init__(
        self, host: str, username: str, password: str, verify_ssl: bool = False
    ):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = None

        # Set default headers
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def authenticate(self) -> bool:
        """Authenticate with VMManager and get token"""
        try:
            auth_url = f"{self.host}/auth/v4/public/token"
            auth_data = {"email": self.username, "password": self.password}

            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()

            auth_result = response.json()
            self.token = auth_result.get("token")

            if self.token:
                self.session.headers.update({"x-xsrf-token": self.token})
                logging.info("Successfully authenticated with VMManager")
                return True
            else:
                logging.error("Failed to get authentication token")
                return False

        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return False

    def check_manager_state(self) -> bool:
        """Check if VMManager API is accessible"""
        try:
            url = f"{self.host}/vm/v3/cluster"
            response = self.session.get(url)
            response.raise_for_status()

            # If we can get clusters list, API is accessible
            clusters_data = response.json()
            if isinstance(clusters_data, dict) and "list" in clusters_data:
                return True
            return len(clusters_data) >= 0  # Even empty list means API is working

        except Exception as e:
            logging.error(f"Failed to check API accessibility: {e}")
            return False

    def get_clusters(self) -> List[ClusterInfo]:
        """Get list of all clusters"""
        try:
            url = f"{self.host}/vm/v3/cluster"
            response = self.session.get(url)
            response.raise_for_status()

            clusters_response = response.json()
            clusters = []

            # API returns object with 'list' field containing clusters array
            if isinstance(clusters_response, dict) and "list" in clusters_response:
                clusters_data = clusters_response["list"]
            else:
                clusters_data = clusters_response

            for cluster_data in clusters_data:
                cluster = ClusterInfo(
                    id=str(cluster_data["id"]),
                    name=cluster_data["name"],
                    nodes=[],
                    balancer_enabled=True,  # External balancer works for all clusters
                )

                # Get nodes for this cluster
                cluster.nodes = self.get_cluster_nodes(cluster.id)
                clusters.append(cluster)

            return clusters

        except Exception as e:
            logging.error(f"Failed to get clusters: {e}")
            return []

    def get_cluster_nodes(self, cluster_id: str) -> List[NodeInfo]:
        """Get nodes for specific cluster"""
        try:
            # Get all nodes and filter by cluster_id on client side
            # Server-side filtering seems to cause 500 errors
            url = f"{self.host}/vm/v3/node"
            response = self.session.get(url)
            response.raise_for_status()

            nodes_response = response.json()
            nodes = []

            # API returns object with 'list' field containing nodes array
            if isinstance(nodes_response, dict) and "list" in nodes_response:
                nodes_data = nodes_response["list"]
            else:
                nodes_data = nodes_response

            for node_data in nodes_data:
                # Filter by cluster_id on client side
                if str(node_data.get("cluster", {}).get("id", "")) != cluster_id:
                    continue

                # Get detailed node statistics from the node data itself
                node = NodeInfo(
                    id=str(node_data["id"]),
                    name=node_data["name"],
                    cpu_total=node_data.get("cpu", {}).get("number", 0),
                    cpu_used=node_data.get("cpu", {}).get("used", 0),
                    memory_total_mb=node_data.get("ram_mib", {}).get("total", 0),
                    memory_used_mb=node_data.get("ram_mib", {}).get("allocated", 0),
                    vm_count=node_data.get("vm", {}).get("total", 0),
                    is_maintenance=node_data.get("maintenance_mode", False)
                    or node_data.get("maintenance", False),
                    vm_creation_allowed=not node_data.get(
                        "host_creation_blocked", False
                    ),
                    vm_limit=node_data.get("host_limit", 0),
                    qemu_version=node_data.get("qemu_version", ""),
                    # SSH parameters from API
                    ssh_host=node_data.get("ip"),  # Use node IP for SSH connection
                    ssh_port=node_data.get(
                        "port", 22
                    ),  # SSH port from API, default to 22
                    ssh_user=node_data.get("ssh_user"),  # SSH user from API
                )
                nodes.append(node)

            return nodes

        except Exception as e:
            logging.error(f"Failed to get cluster nodes: {e}")
            return []

    def get_cluster_vms(self, cluster_id: str) -> List[VMInfo]:
        """Get virtual machines in cluster"""
        try:
            # Get all VMs and filter by cluster_id on client side
            # Server-side filtering seems to cause 500 errors
            url = f"{self.host}/vm/v3/host"
            response = self.session.get(url)
            response.raise_for_status()

            vms_response = response.json()
            vms = []

            # API returns object with 'list' field containing VMs array
            if isinstance(vms_response, dict) and "list" in vms_response:
                vms_data = vms_response["list"]
            else:
                vms_data = vms_response

            logging.debug(
                f"Retrieved {len(vms_data)} VMs from API for cluster {cluster_id}"
            )

            # Debug: log a sample VM to understand the structure
            if vms_data and len(vms_data) > 0:
                sample_vm = vms_data[0]
                logging.debug(f"Sample VM data fields: {list(sample_vm.keys())}")
                if "cluster_id" in sample_vm:
                    logging.debug(f"Sample VM cluster_id: {sample_vm['cluster_id']}")
                else:
                    logging.debug("No 'cluster_id' field found in VM data")
                    # Check for other possible cluster-related fields
                    for key in sample_vm.keys():
                        if "cluster" in key.lower():
                            logging.debug(
                                f"Found cluster-related field: {key} = {sample_vm[key]}"
                            )

            filtered_count = 0
            for vm_data in vms_data:
                # Filter by cluster_id on client side
                # The cluster data is in vm_data['cluster']['id'], not vm_data['cluster_id']
                cluster_data = vm_data.get("cluster", {})
                vm_cluster_id = str(cluster_data.get("id", ""))
                if vm_cluster_id != cluster_id:
                    continue

                filtered_count += 1

                # Check if VM can be migrated
                can_migrate = self.can_vm_migrate(vm_data)

                vm = VMInfo(
                    id=str(vm_data["id"]),
                    name=vm_data["name"],
                    node_id=str(vm_data.get("node", {}).get("id", "")),
                    cpu_cores=vm_data.get("cpu_number", 0),
                    memory_mb=vm_data.get("ram_mib", 0),
                    state=vm_data.get("state", "unknown"),
                    can_migrate=can_migrate,
                )
                vms.append(vm)

            logging.debug(f"Filtered {filtered_count} VMs for cluster {cluster_id}")
            return vms

        except Exception as e:
            logging.error(f"Failed to get cluster VMs: {e}")
            return []

    def can_vm_migrate(self, vm_data: Dict) -> bool:
        """Check if VM can be migrated"""
        # VM cannot be migrated if:
        # - It's powered off
        # - Has ISO mounted
        # - Has snapshots
        # - Balancer is disabled for this VM

        vm_name = vm_data.get("name", "unknown")
        state = vm_data.get("state", "").lower()
        if state != "active":
            logging.debug(
                f"VM {vm_name} cannot migrate: state is '{state}', must be 'active'"
            )
            return False

        # Check for mounted ISOs, snapshots, etc.
        has_iso = vm_data.get("iso_mounted", False)
        has_snapshots = vm_data.get("snapshot_count", 0) > 0
        balancer_disabled = vm_data.get("balancer_mode", "off") == "off"

        if has_iso:
            logging.debug(f"VM {vm_name} cannot migrate: has mounted ISO")
            return False
        if has_snapshots:
            logging.debug(
                f"VM {vm_name} cannot migrate: has"
                f" {vm_data.get('snapshot_count', 0)} snapshots"
            )
            return False
        if balancer_disabled:
            logging.debug(
                f"VM {vm_name} cannot migrate: balancer is disabled (mode:"
                f" {vm_data.get('balancer_mode', 'off')})"
            )
            return False

        return True

    def migrate_vm(self, vm_id: str, target_node_id: str, timeout: int = 3600) -> bool:
        """Migrate VM to target node"""
        try:
            url = f"{self.host}/vm/v3/host/{vm_id}/migrate"
            migrate_data = {
                "node": int(target_node_id)  # Convert to integer as API expects number
            }

            logging.debug(f"Migrating VM {vm_id} to node {target_node_id}")
            logging.debug(f"Migration URL: {url}")
            logging.debug(f"Migration data: {migrate_data}")

            response = self.session.post(url, json=migrate_data)

            # Log response details for debugging
            logging.debug(f"Migration response status: {response.status_code}")
            logging.debug(f"Migration response headers: {dict(response.headers)}")

            try:
                response_data = response.json()
                logging.debug(f"Migration response body: {response_data}")
            except ValueError:
                logging.debug(f"Migration response text: {response.text}")

            response.raise_for_status()

            # Get job ID to track migration progress
            vm_id = str(response.json()["id"])
            if job_id := self.get_job_id(vm_id):
                return self.wait_for_job_completion(job_id, timeout)
            else:
                logging.warning(f"No host_migrate task found for VM {vm_id}")
                return False

        except Exception as e:
            logging.error(f"Failed to migrate VM {vm_id}: {e}")
            return False

    def get_job_id(self, vm_id: str) -> str:
        """Get job ID for specific VM"""
        try:
            url = f"{self.host}/vm/v3/host/{vm_id}/history"
            response = self.session.get(url)
            response.raise_for_status()
            history_data = response.json()
            max_id = history_data["max_id"]

            # Check if history contains tasks
            if "list" in history_data and history_data["list"]:
                tasks = history_data["list"]

                # First check if max_id task is a running host_migrate
                max_id_task = next(
                    (task for task in tasks if task.get("id") == max_id), None
                )
                if (
                    max_id_task
                    and max_id_task.get("name") == "host_migrate"
                    and max_id_task.get("state") == "running"
                ):
                    task_id = str(max_id_task["task"])
                    logging.debug(
                        f"Found running host_migrate task (max_id) {task_id} for VM"
                        f" {vm_id}"
                    )
                    return task_id

                # Find the most recent running host_migrate task
                migrate_tasks = [
                    task
                    for task in tasks
                    if task.get("name") == "host_migrate"
                    and task.get("state") == "running"
                ]

                if migrate_tasks:
                    # Get the most recent one (assuming they are ordered by date_create)
                    latest_task = max(
                        migrate_tasks, key=lambda x: x.get("date_create", "")
                    )
                    task_id = str(latest_task["task"])
                    logging.debug(
                        f"Found running host_migrate task ID {task_id} for VM {vm_id}"
                    )
                    return task_id
                else:
                    logging.warning(
                        f"No running host_migrate tasks found for VM {vm_id}"
                    )
                    return None
            else:
                logging.warning(f"No task history found for VM {vm_id}")
                return None

        except Exception as e:
            logging.error(f"Failed to get job ID for VM {vm_id}: {e}")
            return None

    def wait_for_job_completion(self, job_id: str, timeout: int = 3600) -> bool:
        """Wait for job completion with timeout"""
        try:
            url = f"{self.host}/vm/v3/task/{job_id}"
            start_time = time.time()
            last_progress_log = 0

            logging.info(
                f"Waiting for migration job {job_id} to complete (timeout:"
                f" {timeout//60} minutes)"
            )

            while time.time() - start_time < timeout:
                response = self.session.get(url)
                response.raise_for_status()

                job_data = response.json()
                status = job_data.get("task", {}).get("status", "").lower()

                if status == "complete":
                    elapsed = time.time() - start_time
                    logging.info(
                        f"Migration job {job_id} completed successfully in"
                        f" {elapsed:.1f} seconds"
                    )
                    return True
                elif status == "failed":
                    error_msg = job_data.get("task", {}).get("output", "Unknown error")
                    logging.error(f"Job {job_id} failed: \n{error_msg}")
                    return False

                # Log progress every 60 seconds for long-running migrations
                elapsed = time.time() - start_time
                if elapsed - last_progress_log >= 60:
                    status_info = job_data.get("task", {}).get("status", "unknown")
                    logging.info(
                        f"Migration job {job_id} in progress: {elapsed:.0f}s elapsed, "
                        f"status: '{status_info}'"
                    )
                    last_progress_log = elapsed

                time.sleep(5)  # Wait 5 seconds before next check

            logging.warning(f"Job {job_id} timed out after {timeout} seconds")
            return False

        except Exception as e:
            logging.error(f"Error waiting for job {job_id}: {e}")
            return False

    @staticmethod
    def compare_qemu_versions(source_version: str, target_version: str) -> bool:
        """Compare QEMU versions, returns True if target version is compatible (equal or newer)"""
        if not source_version or not target_version:
            logging.debug(
                f"QEMU version comparison: source='{source_version}',"
                f" target='{target_version}' - incomplete data"
            )
            return (
                True  # If version data is missing, allow migration and let API decide
            )

        try:
            # Parse version strings like "6.2.0" or "7.1.0-1ubuntu1"
            def parse_version(version_str: str) -> Tuple[int, ...]:
                # Extract just the numeric part (before any non-numeric characters)
                import re

                numeric_part = re.match(r"(\d+(?:\.\d+)*)", version_str.strip())
                if numeric_part:
                    return tuple(map(int, numeric_part.group(1).split(".")))
                return (0,)

            source_parsed = parse_version(source_version)
            target_parsed = parse_version(target_version)

            # Target version should be >= source version
            is_compatible = target_parsed >= source_parsed

            logging.debug(
                f"QEMU version comparison: source={source_version} ({source_parsed}) vs"
                f" target={target_version} ({target_parsed}) -"
                f" compatible={is_compatible}"
            )

            return is_compatible

        except Exception as e:
            logging.warning(
                f"Error comparing QEMU versions '{source_version}' and"
                f" '{target_version}': {e}"
            )
            return True  # If parsing fails, allow migration and let API decide
