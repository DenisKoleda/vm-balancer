#!/usr/bin/env python3
"""
VMManager 6 Auto-Balancer Script
Автоматическая балансировка виртуальных машин между узлами кластера
"""

import os
import sys
import time
import logging
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

def get_env_value(key: str, default: str = '') -> str:
    """Get environment variable value, removing comments"""
    value = os.getenv(key, default)
    # Remove comments from environment variables
    if '#' in value:
        value = value.split('#')[0].strip()
    return value

def get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer, removing comments"""
    value = get_env_value(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default

def get_env_float(key: str, default: float) -> float:
    """Get environment variable as float, removing comments"""
    value = get_env_value(key, str(default))
    try:
        return float(value)
    except ValueError:
        return default

def get_env_list(key: str, default: str = '') -> List[str]:
    """Get environment variable as list, removing comments and filtering empty values"""
    value = get_env_value(key, default)
    if not value:
        return []
    # Split by comma and filter out empty strings
    return [item.strip() for item in value.split(',') if item.strip()]

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
    def memory_usage_percent(self) -> float:
        """Calculate memory usage percentage"""
        return (self.memory_used_mb / self.memory_total_mb * 100) if self.memory_total_mb > 0 else 0.0
    
    @property
    def is_overloaded(self) -> bool:
        """Check if node is overloaded based on thresholds"""
        # Note: This will be updated by the balancer with actual thresholds
        # For now using default values, but the balancer will override this check
        cpu_overloaded = self.cpu_allocation_ratio > 7.0  # More than 7:1 vCPU ratio
        memory_overloaded = self.memory_usage_percent > 70
        return cpu_overloaded or memory_overloaded
    
    @property
    def can_accept_vms(self) -> bool:
        """Check if node can accept new VMs (not in maintenance, VM creation allowed, and under VM limit)"""
        vm_limit_ok = self.vm_limit <= 0 or self.vm_count < self.vm_limit  # -1 or 0 means no limit
        return not self.is_maintenance and self.vm_creation_allowed and vm_limit_ok

@dataclass
class ClusterInfo:
    """Information about cluster"""
    id: str
    name: str
    nodes: List[NodeInfo]
    balancer_enabled: bool = False

class VMManagerAPI:
    """VMManager 6 API client"""
    
    def __init__(self, host: str, username: str, password: str, verify_ssl: bool = False):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.token = None
        
        # Set default headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
    def authenticate(self) -> bool:
        """Authenticate with VMManager and get token"""
        try:
            auth_url = f"{self.host}/auth/v4/public/token"
            auth_data = {
                'email': self.username,
                'password': self.password
            }
            
            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()
            
            auth_result = response.json()
            self.token = auth_result.get('token')
            
            if self.token:
                self.session.headers.update({
                    'x-xsrf-token': self.token
                })
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
            if isinstance(clusters_data, dict) and 'list' in clusters_data:
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
            if isinstance(clusters_response, dict) and 'list' in clusters_response:
                clusters_data = clusters_response['list']
            else:
                clusters_data = clusters_response
            
            for cluster_data in clusters_data:
                cluster = ClusterInfo(
                    id=str(cluster_data['id']),
                    name=cluster_data['name'],
                    nodes=[],
                    balancer_enabled=True  # External balancer works for all clusters
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
            if isinstance(nodes_response, dict) and 'list' in nodes_response:
                nodes_data = nodes_response['list']
            else:
                nodes_data = nodes_response
            
            for node_data in nodes_data:
                # Filter by cluster_id on client side
                if str(node_data.get('cluster', {}).get('id', '')) != cluster_id:
                    continue
                
                # Get detailed node statistics from the node data itself
                node = NodeInfo(
                    id=str(node_data['id']),
                    name=node_data['name'],
                    cpu_total=node_data.get('cpu', {}).get('number', 0),
                    cpu_used=node_data.get('cpu', {}).get('used', 0),
                    memory_total_mb=node_data.get('ram_mib', {}).get('total', 0),
                    memory_used_mb=node_data.get('ram_mib', {}).get('allocated', 0),
                    vm_count=node_data.get('vm', {}).get('total', 0),
                    is_maintenance=node_data.get('maintenance_mode', False) or node_data.get('maintenance', False),
                    vm_creation_allowed=not node_data.get('host_creation_blocked', False),  # Use correct API field name
                    vm_limit=node_data.get('host_limit', 0),  # Use correct API field name for VM limit
                    qemu_version=node_data.get('qemu_version', '')  # Use correct API field name for QEMU version
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
            if isinstance(vms_response, dict) and 'list' in vms_response:
                vms_data = vms_response['list']
            else:
                vms_data = vms_response
            
            logging.debug(f"Retrieved {len(vms_data)} VMs from API for cluster {cluster_id}")
            
            # Debug: log a sample VM to understand the structure
            if vms_data and len(vms_data) > 0:
                sample_vm = vms_data[0]
                logging.debug(f"Sample VM data fields: {list(sample_vm.keys())}")
                if 'cluster_id' in sample_vm:
                    logging.debug(f"Sample VM cluster_id: {sample_vm['cluster_id']}")
                else:
                    logging.debug("No 'cluster_id' field found in VM data")
                    # Check for other possible cluster-related fields
                    for key in sample_vm.keys():
                        if 'cluster' in key.lower():
                            logging.debug(f"Found cluster-related field: {key} = {sample_vm[key]}")
            
            filtered_count = 0
            for vm_data in vms_data:
                # Filter by cluster_id on client side
                # The cluster data is in vm_data['cluster']['id'], not vm_data['cluster_id']
                cluster_data = vm_data.get('cluster', {})
                vm_cluster_id = str(cluster_data.get('id', ''))
                if vm_cluster_id != cluster_id:
                    continue
                
                filtered_count += 1
                
                # Check if VM can be migrated
                can_migrate = self.can_vm_migrate(vm_data)
                
                vm = VMInfo(
                    id=str(vm_data['id']),
                    name=vm_data['name'],
                    node_id=str(vm_data.get('node', {}).get('id', '')),
                    cpu_cores=vm_data.get('cpu_number', 0),
                    memory_mb=vm_data.get('ram_mib', 0),
                    state=vm_data.get('state', 'unknown'),
                    can_migrate=can_migrate
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
        
        vm_name = vm_data.get('name', 'unknown')
        state = vm_data.get('state', '').lower()
        if state != 'active':
            logging.debug(f"VM {vm_name} cannot migrate: state is '{state}', must be 'active'")
            return False
            
        # Check for mounted ISOs, snapshots, etc.
        has_iso = vm_data.get('iso_mounted', False)
        has_snapshots = vm_data.get('snapshot_count', 0) > 0
        balancer_disabled = vm_data.get('balancer_mode', 'off') == 'off'
        
        if has_iso:
            logging.debug(f"VM {vm_name} cannot migrate: has mounted ISO")
            return False
        if has_snapshots:
            logging.debug(f"VM {vm_name} cannot migrate: has {vm_data.get('snapshot_count', 0)} snapshots")
            return False
        if balancer_disabled:
            logging.debug(f"VM {vm_name} cannot migrate: balancer is disabled (mode: {vm_data.get('balancer_mode', 'off')})")
            return False
        
        return True
    
    def migrate_vm(self, vm_id: str, target_node_id: str, timeout: int = 3600) -> bool:
        """Migrate VM to target node"""
        try:
            url = f"{self.host}/vm/v3/host/{vm_id}/migrate"
            migrate_data = {
                'node': int(target_node_id)  # Convert to integer as API expects number
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
            except:
                logging.debug(f"Migration response text: {response.text}")
            
            response.raise_for_status()
            
            # Get job ID to track migration progress
            job_data = response.json()
            job_id = job_data.get('id')
            
            if job_id:
                return self.wait_for_job_completion(job_id, timeout)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to migrate VM {vm_id}: {e}")
            return False
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 3600) -> bool:
        """Wait for job completion with timeout"""
        try:
            url = f"{self.host}/vm/v3/task/{job_id}"
            start_time = time.time()
            last_progress_log = 0
            
            logging.info(f"Waiting for migration job {job_id} to complete (timeout: {timeout//60} minutes)")
            
            while time.time() - start_time < timeout:
                response = self.session.get(url)
                response.raise_for_status()
                
                job_data = response.json()
                status = job_data.get('status', '').lower()
                
                if status == 'success':
                    elapsed = time.time() - start_time
                    logging.info(f"Migration job {job_id} completed successfully in {elapsed:.1f} seconds")
                    return True
                elif status == 'error':
                    error_msg = job_data.get('error_message', 'Unknown error')
                    logging.error(f"Job {job_id} failed: {error_msg}")
                    return False
                
                # Log progress every 60 seconds for long-running migrations
                elapsed = time.time() - start_time
                if elapsed - last_progress_log >= 60:
                    progress_msg = job_data.get('progress', 'unknown')
                    status_info = status if status else 'running'
                    
                    # Try to get additional useful information from job data
                    extra_info = []
                    if 'progress_percent' in job_data:
                        extra_info.append(f"percent: {job_data['progress_percent']}%")
                    if 'remaining_time' in job_data:
                        extra_info.append(f"remaining: {job_data['remaining_time']}s")
                    if 'current_step' in job_data:
                        extra_info.append(f"step: {job_data['current_step']}")
                    
                    extra_str = f", {', '.join(extra_info)}" if extra_info else ""
                    
                    logging.info(f"Migration job {job_id} in progress: {elapsed:.0f}s elapsed, "
                               f"status: '{status_info}', progress: '{progress_msg}'{extra_str}")
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
            logging.debug(f"QEMU version comparison: source='{source_version}', target='{target_version}' - incomplete data")
            return True  # If version data is missing, allow migration and let API decide
        
        try:
            # Parse version strings like "6.2.0" or "7.1.0-1ubuntu1"
            def parse_version(version_str: str) -> Tuple[int, ...]:
                # Extract just the numeric part (before any non-numeric characters)
                import re
                numeric_part = re.match(r'(\d+(?:\.\d+)*)', version_str.strip())
                if numeric_part:
                    return tuple(map(int, numeric_part.group(1).split('.')))
                return (0,)
            
            source_parsed = parse_version(source_version)
            target_parsed = parse_version(target_version)
            
            # Target version should be >= source version
            is_compatible = target_parsed >= source_parsed
            
            logging.debug(f"QEMU version comparison: source={source_version} ({source_parsed}) vs "
                         f"target={target_version} ({target_parsed}) - compatible={is_compatible}")
            
            return is_compatible
            
        except Exception as e:
            logging.warning(f"Error comparing QEMU versions '{source_version}' and '{target_version}': {e}")
            return True  # If parsing fails, allow migration and let API decide

class VMBalancer:
    """Main balancer logic"""
    
    def __init__(self, api: VMManagerAPI, dry_run: bool = False, cluster_ids: Optional[List[str]] = None,
                 cpu_overload_threshold: float = 7.0, memory_overload_threshold: float = 70.0,
                 cpu_target_threshold: float = 6.0, memory_target_threshold: float = 80.0,
                 excluded_source_nodes: Optional[List[str]] = None, excluded_target_nodes: Optional[List[str]] = None,
                 max_migrations_per_cycle: int = 1, migration_timeout: int = 1800):
        self.api = api
        self.cpu_overload_threshold = cpu_overload_threshold  # CPU allocation ratio for overloaded nodes
        self.memory_overload_threshold = memory_overload_threshold  # Memory percentage for overloaded nodes
        self.cpu_target_threshold = cpu_target_threshold  # CPU allocation ratio for target nodes
        self.memory_target_threshold = memory_target_threshold  # Memory percentage for target nodes
        self.migration_history = {}  # Track recent migrations
        self.dry_run = dry_run
        self.cluster_ids = cluster_ids  # List of cluster IDs to process (None = all clusters)
        self.excluded_source_nodes = set(excluded_source_nodes or [])  # Nodes to exclude as migration sources
        self.excluded_target_nodes = set(excluded_target_nodes or [])  # Nodes to exclude as migration targets
        self.max_migrations_per_cycle = max_migrations_per_cycle  # Maximum number of migrations per cycle
        self.migration_timeout = migration_timeout  # Timeout for VM migration in seconds
        
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
            logging.warning(f"No clusters found matching specified IDs: {self.cluster_ids}")
        
        return filtered
    
    def find_overloaded_nodes(self, nodes: List[NodeInfo]) -> List[NodeInfo]:
        """Find nodes that are overloaded"""
        overloaded = []
        for node in nodes:
            # Skip excluded source nodes
            if node.name in self.excluded_source_nodes or node.id in self.excluded_source_nodes:
                logging.debug(f"Node {node.name} excluded from migration sources")
                continue
                
            if (not node.is_maintenance and 
                (node.cpu_allocation_ratio > self.cpu_overload_threshold or 
                 node.memory_usage_percent > self.memory_overload_threshold)):
                overloaded.append(node)
        
        # Sort by load (most loaded first)
        overloaded.sort(key=lambda n: max(n.cpu_allocation_ratio, n.memory_usage_percent), reverse=True)
        return overloaded
    
    def find_underloaded_nodes(self, nodes: List[NodeInfo]) -> List[NodeInfo]:
        """Find nodes that have capacity for more VMs"""
        underloaded = []
        for node in nodes:
            # Skip excluded target nodes
            if node.name in self.excluded_target_nodes or node.id in self.excluded_target_nodes:
                logging.debug(f"Node {node.name} excluded from migration targets")
                continue
                
            qemu_info = f", QEMU={node.qemu_version}" if node.qemu_version else ", QEMU=unknown"
            logging.debug(f"Checking node {node.name}: maintenance={node.is_maintenance}, "
                         f"vm_creation_allowed={node.vm_creation_allowed}, vm_count={node.vm_count}, "
                         f"vm_limit={node.vm_limit}, can_accept_vms={node.can_accept_vms}, "
                         f"CPU_ratio={node.cpu_allocation_ratio:.1f}:1 ({node.cpu_used}/{node.cpu_total}), "
                         f"Memory={node.memory_usage_percent:.1f}%{qemu_info}")
            
            # Check if node can accept VMs and has capacity
            cpu_has_capacity = node.cpu_allocation_ratio < self.cpu_target_threshold
            memory_has_capacity = node.memory_usage_percent < self.memory_target_threshold
            
            if (node.can_accept_vms and cpu_has_capacity and memory_has_capacity):
                logging.debug(f"Node {node.name} accepted as underloaded target")
                underloaded.append(node)
            else:
                reasons = []
                if not node.can_accept_vms:
                    if node.is_maintenance:
                        reasons.append("in maintenance")
                    if not node.vm_creation_allowed:
                        reasons.append("VM creation disabled")
                    if node.vm_limit > 0 and node.vm_count >= node.vm_limit:
                        reasons.append(f"VM limit reached ({node.vm_count}/{node.vm_limit})")
                if not cpu_has_capacity:
                    reasons.append(f"CPU allocation too high ({node.cpu_allocation_ratio:.1f}:1)")
                if not memory_has_capacity:
                    reasons.append(f"Memory too high ({node.memory_usage_percent:.1f}%)")
                
                if not reasons:  # If no specific reasons found, add generic message
                    reasons.append("unknown reason")
                
                logging.debug(f"Node {node.name} rejected: {', '.join(reasons)}")
        
        # Sort by available capacity (lowest allocation ratio first)
        underloaded.sort(key=lambda n: (n.cpu_allocation_ratio, n.memory_usage_percent))
        return underloaded
    
    def select_vm_for_migration(self, vms: List[VMInfo], source_node: NodeInfo) -> Optional[VMInfo]:
        """Select best VM candidate for migration from overloaded node"""
        # Filter VMs that can be migrated and are on source node
        all_vms_on_node = [vm for vm in vms if vm.node_id == source_node.id]
        candidates = [vm for vm in all_vms_on_node if vm.can_migrate]
        
        logging.debug(f"Node {source_node.name}: {len(all_vms_on_node)} total VMs, {len(candidates)} can migrate")
        
        if not candidates:
            if all_vms_on_node:
                non_migratable_states = {}
                for vm in all_vms_on_node:
                    if not vm.can_migrate:
                        non_migratable_states[vm.state] = non_migratable_states.get(vm.state, 0) + 1
                
                logging.info(f"Node {source_node.name}: {len(all_vms_on_node)} VMs present, but none can migrate. "
                           f"VM states: {dict(non_migratable_states)}")
            else:
                logging.info(f"Node {source_node.name}: No VMs found on this node")
            return None
        
        # Exclude VMs that were recently migrated
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_candidates = [vm for vm in candidates 
                           if self.migration_history.get(vm.id, datetime.min) < recent_cutoff]
        
        if not recent_candidates:
            logging.info(f"Node {source_node.name}: {len(candidates)} VMs can migrate, "
                        f"but all were recently migrated (within 1 hour)")
            return None
        
        # Sort by resource usage (migrate smaller VMs first for easier balancing)
        recent_candidates.sort(key=lambda vm: vm.cpu_cores + (vm.memory_mb / 1024))
        
        selected_vm = recent_candidates[0]
        logging.debug(f"Node {source_node.name}: Selected VM {selected_vm.name} for migration "
                     f"(CPU: {selected_vm.cpu_cores}, Memory: {selected_vm.memory_mb}MB)")
        
        return selected_vm
    
    def can_node_accept_vm(self, node: NodeInfo, vm: VMInfo) -> bool:
        """Check if node can accept the VM without becoming overloaded"""
        # Estimate resource usage after migration
        estimated_cpu_ratio = (node.cpu_used + vm.cpu_cores) / node.cpu_total
        estimated_memory = node.memory_usage_percent + (vm.memory_mb / node.memory_total_mb * 100)
        
        cpu_ok = estimated_cpu_ratio < self.cpu_overload_threshold  # Use overload threshold for final check
        memory_ok = estimated_memory < self.memory_overload_threshold
        
        # Check QEMU version compatibility
        qemu_ok = True
        source_node = self.get_source_node_for_vm(vm)
        if source_node and node.qemu_version and source_node.qemu_version:
            qemu_ok = self.api.compare_qemu_versions(source_node.qemu_version, node.qemu_version)
            if not qemu_ok:
                logging.warning(f"QEMU version incompatible for VM {vm.name}: "
                               f"source node {source_node.name} has QEMU {source_node.qemu_version}, "
                               f"target node {node.name} has QEMU {node.qemu_version}. "
                               f"Target QEMU version must be equal or newer than source.")
        elif source_node:
            # Log when QEMU version information is missing
            if not node.qemu_version and not source_node.qemu_version:
                logging.debug(f"QEMU version unknown for both source ({source_node.name}) and target ({node.name}) nodes")
            elif not node.qemu_version:
                logging.debug(f"QEMU version unknown for target node {node.name}")
            elif not source_node.qemu_version:
                logging.debug(f"QEMU version unknown for source node {source_node.name}")
        
        logging.debug(f"Can {node.name} accept VM {vm.name}? "
                     f"Current: CPU {node.cpu_allocation_ratio:.1f}:1, Memory {node.memory_usage_percent:.1f}% | "
                     f"After: CPU {estimated_cpu_ratio:.1f}:1, Memory {estimated_memory:.1f}% | "
                     f"CPU_ok={cpu_ok}, Memory_ok={memory_ok}, QEMU_ok={qemu_ok}")
        
        return cpu_ok and memory_ok and qemu_ok
    
    def get_source_node_for_vm(self, vm: VMInfo) -> Optional[NodeInfo]:
        """Find source node for given VM"""
        # This method needs access to current cluster nodes
        # We'll need to pass this information differently
        if hasattr(self, '_current_cluster_nodes'):
            for node in self._current_cluster_nodes:
                if node.id == vm.node_id:
                    return node
        return None
    
    def find_target_node(self, vm: VMInfo, underloaded_nodes: List[NodeInfo]) -> Optional[NodeInfo]:
        """Find suitable target node for VM migration"""
        for node in underloaded_nodes:
            if self.can_node_accept_vm(node, vm):
                return node
        return None
    
    def balance_cluster(self, cluster: ClusterInfo) -> int:
        """Balance VMs in cluster, returns number of migrations performed"""
        logging.info(f"Starting balance check for cluster: {cluster.name}")
        
        # Store current cluster nodes for QEMU version checking
        self._current_cluster_nodes = cluster.nodes
        
        # Log threshold settings
        logging.debug(f"Thresholds - CPU overload: {self.cpu_overload_threshold}:1, "
                     f"Memory overload: {self.memory_overload_threshold}%, "
                     f"CPU target: {self.cpu_target_threshold}:1, "
                     f"Memory target: {self.memory_target_threshold}%")
        
        # Log migration settings
        logging.debug(f"Migration settings - Max migrations per cycle: {self.max_migrations_per_cycle}")
        
        # Log excluded nodes
        if self.excluded_source_nodes:
            logging.info(f"Excluded migration sources: {', '.join(self.excluded_source_nodes)}")
        if self.excluded_target_nodes:
            logging.info(f"Excluded migration targets: {', '.join(self.excluded_target_nodes)}")
        
        # Log nodes with restrictions
        restricted_nodes = [node for node in cluster.nodes if not node.vm_creation_allowed]
        if restricted_nodes:
            restricted_names = [node.name for node in restricted_nodes]
            logging.info(f"Nodes with VM creation disabled: {', '.join(restricted_names)}")
        
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
            if migrations_performed >= self.max_migrations_per_cycle:  # Limit to max_migrations_per_cycle
                break
                
            logging.info(f"Node {source_node.name} is overloaded: "
                        f"CPU allocation {source_node.cpu_allocation_ratio:.1f}:1 ({source_node.cpu_used}/{source_node.cpu_total}), "
                        f"Memory {source_node.memory_usage_percent:.1f}%")
            
            # Select VM to migrate
            vm_to_migrate = self.select_vm_for_migration(cluster_vms, source_node)
            if not vm_to_migrate:
                logging.info(f"No suitable VM found for migration from {source_node.name}")
                continue
            
            # Find target node
            target_node = self.find_target_node(vm_to_migrate, underloaded_nodes)
            if not target_node:
                logging.info(f"No suitable target node found for VM {vm_to_migrate.name}")
                continue
            
            # Perform migration
            logging.info(f"{'[DRY RUN] Would migrate' if self.dry_run else 'Migrating'} VM {vm_to_migrate.name} "
                        f"from {source_node.name} to {target_node.name}")
            
            if self.dry_run:
                # In dry run mode, just log what would be done
                logging.info(f"[DRY RUN] VM {vm_to_migrate.name} migration simulated successfully")
                migrations_performed += 1
                
                # Update node info for simulation
                source_node.vm_count -= 1
                target_node.vm_count += 1
            else:
                # Real migration
                if self.api.migrate_vm(vm_to_migrate.id, target_node.id, self.migration_timeout):
                    logging.info(f"Successfully migrated VM {vm_to_migrate.name}")
                    self.migration_history[vm_to_migrate.id] = datetime.now()
                    migrations_performed += 1
                    
                    # Update node info after migration
                    source_node.vm_count -= 1
                    target_node.vm_count += 1
                    
                    # Remove target node from underloaded list if it's getting full
                    if not self.can_node_accept_vm(target_node, vm_to_migrate):
                        underloaded_nodes.remove(target_node)
                else:
                    logging.error(f"Failed to migrate VM {vm_to_migrate.name}")
        
        # Clean up cluster nodes reference
        self._current_cluster_nodes = None
        
        return migrations_performed
    
    def run_balance_cycle(self) -> None:
        """Run one complete balance cycle for all clusters"""
        mode_text = "[DRY RUN] " if self.dry_run else ""
        logging.info(f"{mode_text}Starting balance cycle")
        
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
        
        total_migrations = 0
        for cluster in clusters:
            try:
                migrations = self.balance_cluster(cluster)
                total_migrations += migrations
            except Exception as e:
                logging.error(f"Error balancing cluster {cluster.name}: {e}")
        
        logging.info(f"{mode_text}Balance cycle completed. Total migrations: {total_migrations}")

def setup_logging(log_level: str = 'INFO') -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('vm_balancer.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='VMManager 6 Auto-Balancer')
    parser.add_argument('--host', 
                       default=get_env_value('VMMANAGER_HOST', 'https://localhost'),
                       help='VMManager host URL')
    parser.add_argument('--username', 
                       default=get_env_value('VMMANAGER_USERNAME', 'admin'),
                       help='VMManager username')
    parser.add_argument('--password', 
                       default=get_env_value('VMMANAGER_PASSWORD'),
                       help='VMManager password')
    parser.add_argument('--interval', 
                       type=int, 
                       default=get_env_int('BALANCE_INTERVAL', 600),
                       help='Balance check interval in seconds (default: 600)')
    parser.add_argument('--cluster-ids',
                       nargs='*',
                       default=get_env_value('CLUSTER_IDS', '').split(',') if get_env_value('CLUSTER_IDS') else None,
                       help='Specific cluster IDs to process (space-separated). If not specified, all clusters will be processed')
    parser.add_argument('--cpu-overload-threshold',
                       type=float,
                       default=get_env_float('CPU_OVERLOAD_THRESHOLD', 7.0),
                       help='CPU allocation ratio threshold for overloaded nodes (default: 7.0)')
    parser.add_argument('--memory-overload-threshold',
                       type=float,
                       default=get_env_float('MEMORY_OVERLOAD_THRESHOLD', 70.0),
                       help='Memory usage percentage threshold for overloaded nodes (default: 70.0)')
    parser.add_argument('--cpu-target-threshold',
                       type=float,
                       default=get_env_float('CPU_TARGET_THRESHOLD', 6.0),
                       help='CPU allocation ratio threshold for target nodes (default: 6.0)')
    parser.add_argument('--memory-target-threshold',
                       type=float,
                       default=get_env_float('MEMORY_TARGET_THRESHOLD', 80.0),
                       help='Memory usage percentage threshold for target nodes (default: 80.0)')
    parser.add_argument('--exclude-source-nodes',
                       nargs='*',
                       default=get_env_list('EXCLUDE_SOURCE_NODES'),
                       help='Node names or IDs to exclude as migration sources (space-separated)')
    parser.add_argument('--exclude-target-nodes',
                       nargs='*',
                       default=get_env_list('EXCLUDE_TARGET_NODES'),
                       help='Node names or IDs to exclude as migration targets (space-separated)')
    parser.add_argument('--max-migrations-per-cycle',
                       type=int,
                       default=get_env_int('MAX_MIGRATIONS_PER_CYCLE', 1),
                       help='Maximum number of VM migrations per cycle (default: 1)')
    parser.add_argument('--migration-timeout',
                       type=int,
                       default=get_env_int('MIGRATION_TIMEOUT', 1800),
                       help='Timeout for VM migration in seconds (default: 1800 = 30 minutes)')
    parser.add_argument('--once', 
                       action='store_true',
                       help='Run once and exit')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Simulate migrations without actually performing them')
    parser.add_argument('--log-level', 
                       default=get_env_value('LOG_LEVEL', 'INFO'),
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--verify-ssl', 
                       action='store_true',
                       help='Verify SSL certificates')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Check required parameters
    if not args.password:
        logging.error("Password is required. Set VMMANAGER_PASSWORD env var or use --password")
        sys.exit(1)
    
    if args.dry_run:
        logging.info("Running in DRY RUN mode - no actual migrations will be performed")
    
    # Process cluster IDs
    cluster_ids = None
    if args.cluster_ids:
        # Filter out empty strings from splitting
        cluster_ids = [cid.strip() for cid in args.cluster_ids if cid.strip()]
        if cluster_ids:
            logging.info(f"Will process only clusters with IDs: {cluster_ids}")
        else:
            cluster_ids = None
    
    # Initialize API client
    api = VMManagerAPI(
        host=args.host,
        username=args.username,
        password=args.password,
        verify_ssl=args.verify_ssl
    )
    
    # Authenticate
    if not api.authenticate():
        logging.error("Failed to authenticate with VMManager")
        sys.exit(1)
    
    # Initialize balancer
    balancer = VMBalancer(api, dry_run=args.dry_run, cluster_ids=cluster_ids,
                         cpu_overload_threshold=args.cpu_overload_threshold,
                         memory_overload_threshold=args.memory_overload_threshold,
                         cpu_target_threshold=args.cpu_target_threshold,
                         memory_target_threshold=args.memory_target_threshold,
                         excluded_source_nodes=args.exclude_source_nodes,
                         excluded_target_nodes=args.exclude_target_nodes,
                         max_migrations_per_cycle=args.max_migrations_per_cycle,
                         migration_timeout=args.migration_timeout)
    
    # Run balancer
    if args.once:
        # Run once and exit
        balancer.run_balance_cycle()
    else:
        # Run continuously
        mode_text = " (DRY RUN mode)" if args.dry_run else ""
        logging.info(f"Starting continuous balancing with {args.interval}s interval{mode_text}")
        logging.info("Press Ctrl+C to stop")
        
        try:
            while True:
                balancer.run_balance_cycle()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logging.info("Balancer stopped by user")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()
