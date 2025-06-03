#!/usr/bin/env python3
"""
VMManager 6 Auto-Balancer Interactive Mode
Интерактивный режим для управления балансировщиком ВМ
"""

import os
import sys
import time
import threading
from typing import Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, TaskID
from rich import box
from rich.align import Align
from dotenv import load_dotenv

# Import classes from main balancer module
try:
    from vm_balancer import (
        VMManagerAPI, VMBalancer, NodeInfo, VMInfo, ClusterInfo,
        get_env_value, get_env_int, get_env_float, get_env_list,
        setup_logging
    )
except ImportError:
    # If import fails, try with different module name
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("vm_balancer", "vm_balancer.py")
        vm_balancer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vm_balancer)
        
        VMManagerAPI = vm_balancer.VMManagerAPI
        VMBalancer = vm_balancer.VMBalancer
        NodeInfo = vm_balancer.NodeInfo
        VMInfo = vm_balancer.VMInfo
        ClusterInfo = vm_balancer.ClusterInfo
        get_env_value = vm_balancer.get_env_value
        get_env_int = vm_balancer.get_env_int
        get_env_float = vm_balancer.get_env_float
        get_env_list = vm_balancer.get_env_list
        setup_logging = vm_balancer.setup_logging
    except Exception as e:
        print(f"Error importing VM balancer module: {e}")
        print("Make sure vm_balancer.py is in the same directory")
        sys.exit(1)

# Load environment variables
load_dotenv()

class InteractiveBalancer:
    """Interactive balancer with console GUI"""
    
    def __init__(self):
        self.console = Console()
        self.api: Optional[VMManagerAPI] = None
        self.balancer: Optional[VMBalancer] = None
        self.clusters: List[ClusterInfo] = []
        self.is_connected = False
        self.balance_thread: Optional[threading.Thread] = None
        self.balance_running = False
        
        # Default settings
        self.settings = {
            'host': get_env_value('VMMANAGER_HOST', 'https://localhost'),
            'username': get_env_value('VMMANAGER_USERNAME', 'admin'),
            'password': get_env_value('VMMANAGER_PASSWORD', ''),
            'verify_ssl': False,
            'cpu_overload_threshold': get_env_float('CPU_OVERLOAD_THRESHOLD', 7.0),
            'memory_overload_threshold': get_env_float('MEMORY_OVERLOAD_THRESHOLD', 70.0),
            'cpu_target_threshold': get_env_float('CPU_TARGET_THRESHOLD', 6.0),
            'memory_target_threshold': get_env_float('MEMORY_TARGET_THRESHOLD', 80.0),
            'max_migrations_per_cycle': get_env_int('MAX_MIGRATIONS_PER_CYCLE', 1),
            'balance_interval': get_env_int('BALANCE_INTERVAL', 600),
            'cluster_ids': get_env_list('CLUSTER_IDS'),
            'exclude_source_nodes': get_env_list('EXCLUDE_SOURCE_NODES'),
            'exclude_target_nodes': get_env_list('EXCLUDE_TARGET_NODES'),
            'dry_run': False
        }
    
    def create_header(self) -> Panel:
        """Create header panel"""
        status = "[green]Connected[/green]" if self.is_connected else "[red]Disconnected[/red]"
        balance_status = "[yellow]Running[/yellow]" if self.balance_running else "[dim]Stopped[/dim]"
        
        header_text = f"""[bold]VMManager 6 Auto-Balancer Interactive Mode[/bold]
Status: {status} | Balance: {balance_status} | Time: {datetime.now().strftime('%H:%M:%S')}"""
        
        return Panel(
            Align.center(header_text),
            box=box.ROUNDED,
            style="blue"
        )
    
    def create_main_menu(self) -> Table:
        """Create main menu table"""
        table = Table(show_header=False, box=box.ROUNDED, expand=True)
        table.add_column("Option", style="cyan", width=4)
        table.add_column("Description", style="white")
        table.add_column("Status", style="green", width=15)
        
        # Connection status
        conn_status = "✓ Connected" if self.is_connected else "✗ Not connected"
        table.add_row("1", "Connect to VMManager", conn_status)
        
        # Cluster info
        cluster_status = f"{len(self.clusters)} clusters" if self.clusters else "No data"
        table.add_row("2", "View Clusters & Nodes", cluster_status)
        
        # Settings
        dry_run_text = " (Dry Run)" if self.settings['dry_run'] else ""
        table.add_row("3", "Balancer Settings", f"Configured{dry_run_text}")
        
        # Balance operations
        balance_status = "Running" if self.balance_running else "Stopped"
        table.add_row("4", "Run Balance (Once)", balance_status)
        table.add_row("5", "Start/Stop Continuous Balance", balance_status)
        
        # Logs and exit
        table.add_row("6", "View Recent Logs", "Available")
        table.add_row("0", "Exit", "")
        
        return table
    
    def create_clusters_table(self) -> Table:
        """Create clusters overview table"""
        table = Table(box=box.ROUNDED, expand=True)
        table.add_column("Cluster", style="cyan")
        table.add_column("Nodes", justify="center")
        table.add_column("Total VMs", justify="center")
        table.add_column("Overloaded", justify="center", style="red")
        table.add_column("Available", justify="center", style="green")
        table.add_column("Status", style="yellow")
        
        for cluster in self.clusters:
            overloaded = sum(1 for node in cluster.nodes 
                           if node.cpu_allocation_ratio > self.settings['cpu_overload_threshold'] 
                           or node.memory_usage_percent > self.settings['memory_overload_threshold'])
            available = sum(1 for node in cluster.nodes if node.can_accept_vms)
            total_vms = sum(node.vm_count for node in cluster.nodes)
            
            status = "⚠️ Needs Balance" if overloaded > 0 else "✅ Balanced"
            
            table.add_row(
                cluster.name,
                str(len(cluster.nodes)),
                str(total_vms),
                str(overloaded),
                str(available),
                status
            )
        
        return table
    
    def create_nodes_table(self, cluster: ClusterInfo) -> Table:
        """Create detailed nodes table for a cluster"""
        table = Table(box=box.ROUNDED, expand=True, title=f"Nodes in {cluster.name}")
        table.add_column("Node", style="cyan")
        table.add_column("VMs", justify="center")
        table.add_column("CPU Ratio", justify="center")
        table.add_column("Memory %", justify="center") 
        table.add_column("Status", style="yellow")
        table.add_column("Can Accept", justify="center")
        
        for node in cluster.nodes:
            # Color code based on load
            cpu_style = "red" if node.cpu_allocation_ratio > self.settings['cpu_overload_threshold'] else "green"
            memory_style = "red" if node.memory_usage_percent > self.settings['memory_overload_threshold'] else "green"
            
            status_parts = []
            if node.is_maintenance:
                status_parts.append("🔧 Maintenance")
            if not node.vm_creation_allowed:
                status_parts.append("🚫 No VM Creation")
            if node.vm_limit > 0 and node.vm_count >= node.vm_limit:
                status_parts.append(f"📊 Limit ({node.vm_count}/{node.vm_limit})")
            
            status = " | ".join(status_parts) if status_parts else "✅ Normal"
            can_accept = "✅" if node.can_accept_vms else "❌"
            
            table.add_row(
                node.name,
                str(node.vm_count),
                f"[{cpu_style}]{node.cpu_allocation_ratio:.1f}:1[/{cpu_style}]",
                f"[{memory_style}]{node.memory_usage_percent:.1f}%[/{memory_style}]",
                status,
                can_accept
            )
        
        return table
    
    def create_settings_table(self) -> Table:
        """Create settings table"""
        table = Table(box=box.ROUNDED, expand=True, title="Balancer Settings")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Description", style="dim")
        
        settings_info = [
            ("Host", self.settings['host'], "VMManager API endpoint"),
            ("Username", self.settings['username'], "API username"),
            ("Password", "***" if self.settings['password'] else "Not set", "API password"),
            ("SSL Verify", str(self.settings['verify_ssl']), "Verify SSL certificates"),
            ("CPU Overload", f"{self.settings['cpu_overload_threshold']}:1", "CPU allocation ratio threshold"),
            ("Memory Overload", f"{self.settings['memory_overload_threshold']}%", "Memory usage threshold"),
            ("CPU Target", f"{self.settings['cpu_target_threshold']}:1", "Target CPU allocation ratio"),
            ("Memory Target", f"{self.settings['memory_target_threshold']}%", "Target memory usage"),
            ("Max Migrations", str(self.settings['max_migrations_per_cycle']), "Migrations per cycle"),
            ("Balance Interval", f"{self.settings['balance_interval']}s", "Continuous balance interval"),
            ("Cluster IDs", str(self.settings['cluster_ids']) if self.settings['cluster_ids'] else "All", "Target clusters"),
            ("Exclude Sources", str(self.settings['exclude_source_nodes']) if self.settings['exclude_source_nodes'] else "None", "Excluded source nodes"),
            ("Exclude Targets", str(self.settings['exclude_target_nodes']) if self.settings['exclude_target_nodes'] else "None", "Excluded target nodes"),
            ("Dry Run", str(self.settings['dry_run']), "Simulation mode")
        ]
        
        for setting, value, description in settings_info:
            table.add_row(setting, value, description)
        
        return table
    
    def connect_to_vmmanager(self) -> bool:
        """Connect to VMManager API"""
        self.console.print("[yellow]Connecting to VMManager...[/yellow]")
        
        # Check if password is set
        if not self.settings['password']:
            password = Prompt.ask("Enter VMManager password", password=True)
            if not password:
                self.console.print("[red]Password is required[/red]")
                return False
            self.settings['password'] = password
        
        try:
            # Create API client
            self.api = VMManagerAPI(
                host=self.settings['host'],
                username=self.settings['username'],
                password=self.settings['password'],
                verify_ssl=self.settings['verify_ssl']
            )
            
            # Authenticate
            if not self.api.authenticate():
                self.console.print("[red]Authentication failed[/red]")
                return False
            
            # Load clusters
            self.clusters = self.api.get_clusters()
            self.is_connected = True
            
            self.console.print(f"[green]Successfully connected! Found {len(self.clusters)} clusters[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]Connection failed: {e}[/red]")
            return False
    
    def view_clusters(self) -> None:
        """View clusters and nodes"""
        if not self.is_connected:
            self.console.print("[red]Not connected to VMManager[/red]")
            return
        
        while True:
            self.console.clear()
            self.console.print(self.create_header())
            self.console.print("\n")
            self.console.print(self.create_clusters_table())
            
            self.console.print("\n[cyan]Options:[/cyan]")
            self.console.print("1-9: View cluster details | R: Refresh | B: Back to main menu")
            
            choice = Prompt.ask("Choose option").upper()
            
            if choice == 'B':
                break
            elif choice == 'R':
                try:
                    self.clusters = self.api.get_clusters()
                    self.console.print("[green]Data refreshed[/green]")
                except Exception as e:
                    self.console.print(f"[red]Refresh failed: {e}[/red]")
                time.sleep(1)
            elif choice.isdigit() and 1 <= int(choice) <= len(self.clusters):
                cluster_idx = int(choice) - 1
                self.view_cluster_details(self.clusters[cluster_idx])
    
    def view_cluster_details(self, cluster: ClusterInfo) -> None:
        """View detailed cluster information"""
        while True:
            self.console.clear()
            self.console.print(self.create_header())
            self.console.print("\n")
            self.console.print(self.create_nodes_table(cluster))
            
            self.console.print("\n[cyan]Options:[/cyan]")
            self.console.print("R: Refresh | B: Back to clusters list")
            
            choice = Prompt.ask("Choose option").upper()
            
            if choice == 'B':
                break
            elif choice == 'R':
                try:
                    # Refresh cluster data
                    updated_clusters = self.api.get_clusters()
                    for updated_cluster in updated_clusters:
                        if updated_cluster.id == cluster.id:
                            cluster.nodes = updated_cluster.nodes
                            break
                    self.console.print("[green]Data refreshed[/green]")
                except Exception as e:
                    self.console.print(f"[red]Refresh failed: {e}[/red]")
                time.sleep(1)
    
    def configure_settings(self) -> None:
        """Configure balancer settings"""
        while True:
            self.console.clear()
            self.console.print(self.create_header())
            self.console.print("\n")
            self.console.print(self.create_settings_table())
            
            self.console.print("\n[cyan]Options:[/cyan]")
            self.console.print("1: Connection | 2: Thresholds | 3: Exclusions | 4: Other | D: Toggle Dry Run | B: Back")
            
            choice = Prompt.ask("Choose option").upper()
            
            if choice == 'B':
                break
            elif choice == '1':
                self.configure_connection()
            elif choice == '2':
                self.configure_thresholds()
            elif choice == '3':
                self.configure_exclusions()
            elif choice == '4':
                self.configure_other()
            elif choice == 'D':
                self.settings['dry_run'] = not self.settings['dry_run']
                mode = "enabled" if self.settings['dry_run'] else "disabled"
                self.console.print(f"[yellow]Dry run mode {mode}[/yellow]")
                time.sleep(1)
    
    def configure_connection(self) -> None:
        """Configure connection settings"""
        self.console.print("[cyan]Connection Settings[/cyan]")
        
        new_host = Prompt.ask("VMManager host", default=self.settings['host'])
        new_username = Prompt.ask("Username", default=self.settings['username'])
        new_verify_ssl = Confirm.ask("Verify SSL certificates", default=self.settings['verify_ssl'])
        
        self.settings['host'] = new_host
        self.settings['username'] = new_username
        self.settings['verify_ssl'] = new_verify_ssl
        
        # Reset connection if settings changed
        if self.is_connected:
            if Confirm.ask("Settings changed. Reconnect now?"):
                self.is_connected = False
                self.connect_to_vmmanager()
    
    def configure_thresholds(self) -> None:
        """Configure threshold settings"""
        self.console.print("[cyan]Threshold Settings[/cyan]")
        
        try:
            cpu_overload = float(Prompt.ask("CPU overload threshold (ratio)", 
                                          default=str(self.settings['cpu_overload_threshold'])))
            memory_overload = float(Prompt.ask("Memory overload threshold (%)", 
                                             default=str(self.settings['memory_overload_threshold'])))
            cpu_target = float(Prompt.ask("CPU target threshold (ratio)", 
                                        default=str(self.settings['cpu_target_threshold'])))
            memory_target = float(Prompt.ask("Memory target threshold (%)", 
                                           default=str(self.settings['memory_target_threshold'])))
            
            self.settings['cpu_overload_threshold'] = cpu_overload
            self.settings['memory_overload_threshold'] = memory_overload
            self.settings['cpu_target_threshold'] = cpu_target
            self.settings['memory_target_threshold'] = memory_target
            
            self.console.print("[green]Thresholds updated[/green]")
            
        except ValueError:
            self.console.print("[red]Invalid input. Please enter numeric values.[/red]")
        
        time.sleep(1)
    
    def configure_exclusions(self) -> None:
        """Configure node exclusions"""
        self.console.print("[cyan]Node Exclusions[/cyan]")
        
        exclude_sources = Prompt.ask("Exclude source nodes (comma-separated)", 
                                   default=','.join(self.settings['exclude_source_nodes']))
        exclude_targets = Prompt.ask("Exclude target nodes (comma-separated)", 
                                   default=','.join(self.settings['exclude_target_nodes']))
        
        self.settings['exclude_source_nodes'] = [node.strip() for node in exclude_sources.split(',') if node.strip()]
        self.settings['exclude_target_nodes'] = [node.strip() for node in exclude_targets.split(',') if node.strip()]
        
        self.console.print("[green]Exclusions updated[/green]")
        time.sleep(1)
    
    def configure_other(self) -> None:
        """Configure other settings"""
        self.console.print("[cyan]Other Settings[/cyan]")
        
        try:
            max_migrations = int(Prompt.ask("Max migrations per cycle", 
                                          default=str(self.settings['max_migrations_per_cycle'])))
            balance_interval = int(Prompt.ask("Balance interval (seconds)", 
                                            default=str(self.settings['balance_interval'])))
            cluster_ids = Prompt.ask("Cluster IDs (comma-separated, empty for all)", 
                                   default=','.join(self.settings['cluster_ids']))
            
            self.settings['max_migrations_per_cycle'] = max_migrations
            self.settings['balance_interval'] = balance_interval
            self.settings['cluster_ids'] = [cid.strip() for cid in cluster_ids.split(',') if cid.strip()]
            
            self.console.print("[green]Settings updated[/green]")
            
        except ValueError:
            self.console.print("[red]Invalid input. Please enter valid numbers.[/red]")
        
        time.sleep(1)
    
    def run_balance_once(self) -> None:
        """Run balance cycle once"""
        if not self.is_connected:
            self.console.print("[red]Not connected to VMManager[/red]")
            return
        
        if self.balance_running:
            self.console.print("[yellow]Continuous balance is already running[/yellow]")
            return
        
        self.console.print("[yellow]Running balance cycle...[/yellow]")
        
        try:
            # Create balancer with current settings
            balancer = VMBalancer(
                api=self.api,
                dry_run=self.settings['dry_run'],
                cluster_ids=self.settings['cluster_ids'] if self.settings['cluster_ids'] else None,
                cpu_overload_threshold=self.settings['cpu_overload_threshold'],
                memory_overload_threshold=self.settings['memory_overload_threshold'],
                cpu_target_threshold=self.settings['cpu_target_threshold'],
                memory_target_threshold=self.settings['memory_target_threshold'],
                excluded_source_nodes=self.settings['exclude_source_nodes'],
                excluded_target_nodes=self.settings['exclude_target_nodes'],
                max_migrations_per_cycle=self.settings['max_migrations_per_cycle']
            )
            
            # Run balance cycle
            balancer.run_balance_cycle()
            
            # Refresh cluster data
            self.clusters = self.api.get_clusters()
            
            mode_text = " (Dry Run)" if self.settings['dry_run'] else ""
            self.console.print(f"[green]Balance cycle completed{mode_text}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Balance failed: {e}[/red]")
        
        Prompt.ask("Press Enter to continue")
    
    def toggle_continuous_balance(self) -> None:
        """Start or stop continuous balance"""
        if not self.is_connected:
            self.console.print("[red]Not connected to VMManager[/red]")
            return
        
        if self.balance_running:
            # Stop continuous balance
            self.balance_running = False
            if self.balance_thread and self.balance_thread.is_alive():
                self.balance_thread.join(timeout=5)
            self.console.print("[green]Continuous balance stopped[/green]")
        else:
            # Start continuous balance
            self.balance_running = True
            self.balance_thread = threading.Thread(target=self._continuous_balance_worker, daemon=True)
            self.balance_thread.start()
            
            mode_text = " (Dry Run)" if self.settings['dry_run'] else ""
            self.console.print(f"[green]Continuous balance started{mode_text}[/green]")
            self.console.print(f"[dim]Interval: {self.settings['balance_interval']} seconds[/dim]")
        
        time.sleep(1)
    
    def _continuous_balance_worker(self) -> None:
        """Worker thread for continuous balance"""
        try:
            balancer = VMBalancer(
                api=self.api,
                dry_run=self.settings['dry_run'],
                cluster_ids=self.settings['cluster_ids'] if self.settings['cluster_ids'] else None,
                cpu_overload_threshold=self.settings['cpu_overload_threshold'],
                memory_overload_threshold=self.settings['memory_overload_threshold'],
                cpu_target_threshold=self.settings['cpu_target_threshold'],
                memory_target_threshold=self.settings['memory_target_threshold'],
                excluded_source_nodes=self.settings['exclude_source_nodes'],
                excluded_target_nodes=self.settings['exclude_target_nodes'],
                max_migrations_per_cycle=self.settings['max_migrations_per_cycle']
            )
            
            while self.balance_running:
                try:
                    balancer.run_balance_cycle()
                    # Refresh cluster data periodically
                    self.clusters = self.api.get_clusters()
                except Exception as e:
                    # Log error but continue running
                    pass
                
                # Wait for interval, but check balance_running flag every second
                for _ in range(self.settings['balance_interval']):
                    if not self.balance_running:
                        break
                    time.sleep(1)
                    
        except Exception as e:
            self.balance_running = False
    
    def view_logs(self) -> None:
        """View recent log entries"""
        self.console.print("[cyan]Recent log entries (last 50 lines):[/cyan]")
        
        try:
            with open('vm_balancer.log', 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    line = line.strip()
                    if 'ERROR' in line:
                        self.console.print(f"[red]{line}[/red]")
                    elif 'WARNING' in line:
                        self.console.print(f"[yellow]{line}[/yellow]")
                    elif 'INFO' in line:
                        self.console.print(f"[white]{line}[/white]")
                    else:
                        self.console.print(f"[dim]{line}[/dim]")
                        
        except FileNotFoundError:
            self.console.print("[yellow]Log file not found[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error reading logs: {e}[/red]")
        
        Prompt.ask("Press Enter to continue")
    
    def run(self) -> None:
        """Run interactive interface"""
        # Setup logging
        setup_logging('INFO')
        
        self.console.print("[bold green]VMManager 6 Auto-Balancer Interactive Mode[/bold green]")
        self.console.print("Loading settings from environment variables...\n")
        
        # Try to auto-connect if credentials are available
        if self.settings['password']:
            self.connect_to_vmmanager()
        
        while True:
            self.console.clear()
            self.console.print(self.create_header())
            self.console.print("\n")
            self.console.print(Panel(self.create_main_menu(), title="Main Menu", box=box.ROUNDED))
            
            choice = Prompt.ask("Choose option")
            
            if choice == '0':
                if self.balance_running:
                    if Confirm.ask("Continuous balance is running. Stop and exit?"):
                        self.balance_running = False
                        break
                else:
                    break
            elif choice == '1':
                self.connect_to_vmmanager()
            elif choice == '2':
                self.view_clusters()
            elif choice == '3':
                self.configure_settings()
            elif choice == '4':
                self.run_balance_once()
            elif choice == '5':
                self.toggle_continuous_balance()
            elif choice == '6':
                self.view_logs()
            else:
                self.console.print("[red]Invalid option[/red]")
                time.sleep(1)
        
        # Cleanup
        if self.balance_running:
            self.balance_running = False
            if self.balance_thread and self.balance_thread.is_alive():
                self.balance_thread.join(timeout=5)
        
        self.console.print("[green]Goodbye![/green]")

def main():
    """Main function"""
    app = InteractiveBalancer()
    try:
        app.run()
    except KeyboardInterrupt:
        app.console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        app.console.print(f"\n[red]Unexpected error: {e}[/red]")

if __name__ == '__main__':
    main() 