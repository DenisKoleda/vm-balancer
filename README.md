# VMManager 6 Auto-Balancer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An intelligent auto-balancer for VMManager 6 that automatically redistributes virtual machines across cluster nodes to optimize resource utilization and prevent overloading.

## 🚀 Features

- **🔄 Automatic Load Balancing**: Intelligent VM migration from overloaded to underloaded nodes
- **🖥️ Interactive Console UI**: Rich terminal interface for real-time management
- **🎯 Smart Filtering**: Target specific clusters and exclude problematic nodes
- **⚡ Configurable Thresholds**: Flexible CPU and memory thresholds for optimization
- **🛡️ Safety First**: Built-in checks for VM constraints, limits, and maintenance mode
- **🧪 Dry Run Mode**: Test balancing strategies without actual migrations
- **📊 Detailed Logging**: Comprehensive logs for monitoring and troubleshooting
- **🔁 Batch Processing**: Configurable migration limits per cycle for controlled balancing

## 📋 Requirements

- Python 3.8+
- VMManager 6 with API access
- Network connectivity to VMManager API endpoint

## 🔧 Installation

### 📦 From Package (Recommended)

1. **Install from PyPI** (when published):
   ```bash
   pip install vm-balancer
   ```

2. **Or install from source**:
   ```bash
   git clone https://github.com/your-username/vm_balancer.git
   cd vm_balancer
   pip install .
   ```

3. **Configure settings**:
   ```bash
   cp config.env.example .env
   # Edit .env with your VMManager details
   ```

### 🛠️ Development Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/vm_balancer.git
   cd vm_balancer
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install in development mode**:
   ```bash
   pip install -e .
   ```

4. **Configure settings**:
   ```bash
   cp config.env.example .env
   # Edit .env with your VMManager details
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with your VMManager settings:

```bash
# VMManager connection
VMMANAGER_HOST=https://your-vmmanager.com
VMMANAGER_USERNAME=admin
VMMANAGER_PASSWORD=your_password

# Balancing settings
BALANCE_INTERVAL=600                    # Check interval (seconds)
CLUSTER_IDS=1,2,3                      # Target clusters (empty = all)
MAX_MIGRATIONS_PER_CYCLE=1              # Migrations per cycle

# Load thresholds
CPU_OVERLOAD_THRESHOLD=7.0              # CPU allocation ratio trigger
MEMORY_OVERLOAD_THRESHOLD=70.0          # Memory usage % trigger
CPU_TARGET_THRESHOLD=6.0                # CPU target ratio
MEMORY_TARGET_THRESHOLD=80.0            # Memory target %

# Node exclusions
EXCLUDE_SOURCE_NODES=node1,node2        # Exclude as sources
EXCLUDE_TARGET_NODES=node3,node4        # Exclude as targets

# Logging
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR

# SSH Monitoring (Optional)
SSH_ENABLED=false                       # Enable SSH load monitoring
SSH_USERNAME=root                       # SSH username
SSH_PRIVATE_KEY_PATH=/path/to/key       # SSH private key path
SSH_PASSWORD=                           # SSH password (if no key)
SSH_TIMEOUT=10                          # SSH timeout (seconds)
SSH_HOSTS_MAPPING={"node1": "192.168.1.10"}  # Node name to IP mapping

# Telegram Notifications (Optional)
TELEGRAM_BOT_TOKEN=                     # Bot token
TELEGRAM_CHAT_ID=                       # Chat ID
```

### SSH Load Monitoring

The balancer can optionally use SSH to get real-time load average from cluster nodes instead of relying only on VMManager API data. This provides more accurate CPU load information.

**Benefits:**
- Real-time load average (1min, 5min, 15min) from `/proc/loadavg`
- More accurate than vCPU allocation ratios
- Better migration decisions based on actual system load

**Setup:**
1. Enable SSH monitoring in configuration
2. Configure SSH credentials (key or password authentication)
3. API automatically provides IP, port, and username
4. Optionally override with custom hostname mapping

**SSH Authentication Options:**

*Key-based authentication (recommended):*
```bash
SSH_ENABLED=true
SSH_PRIVATE_KEY_PATH=/root/.ssh/id_rsa
SSH_USERNAME=  # Optional fallback, API provides username
```

*Password-based authentication:*
```bash
SSH_ENABLED=true
SSH_PASSWORD=your_ssh_password
SSH_USERNAME=  # Optional fallback, API provides username
```

**Example SSH configuration:**
```bash
# Enable SSH monitoring
SSH_ENABLED=true
SSH_TIMEOUT=10

# Authentication (choose one method)
SSH_PRIVATE_KEY_PATH=/root/.ssh/id_rsa  # Key-based
# SSH_PASSWORD=mysecretpassword         # Password-based

# Optional: Override API-provided hostnames
SSH_HOSTS_MAPPING='{
  "node-1": "192.168.1.10",
  "node-2": "192.168.1.11", 
  "node-3": "node3.example.com"
}'
```

**SSH options:**
```bash
--ssh-enabled                           # Enable SSH monitoring
--ssh-username root                     # SSH username
--ssh-private-key /path/to/key          # SSH private key
--ssh-password mypassword               # SSH password
--ssh-timeout 10                        # Connection timeout
--ssh-hosts-mapping '{"node1":"ip"}'    # JSON hostname mapping
```

### Command Line Options

```bash
# Connection
--host https://vmmanager.example.com    # VMManager URL
--username admin                        # Username
--password mypassword                   # Password
--cluster-ids 1 2 3                     # Target clusters

# Thresholds
--cpu-overload-threshold 7.0            # CPU overload trigger
--memory-overload-threshold 70.0        # Memory overload trigger
--cpu-target-threshold 6.0              # CPU target limit
--memory-target-threshold 80.0          # Memory target limit

# Node filtering
--exclude-source-nodes node1 node2      # Exclude sources
--exclude-target-nodes node3 node4      # Exclude targets

# Migration control
--max-migrations-per-cycle 3            # Max migrations per cycle

# Operation modes
--once                                  # Single run
--dry-run                              # Simulation mode
--interval 600                         # Continuous mode interval
--log-level DEBUG                      # Logging level
--verify-ssl                           # SSL verification
```

## 🎮 Usage

### Command Line Interface

After installation, you can use the `vm-balancer` command:

#### First Run (Recommended)
```bash
# Test without making changes
vm-balancer --dry-run --once --log-level DEBUG
```

#### Single Balancing Run
```bash
vm-balancer --once
```

#### Continuous Monitoring
```bash
vm-balancer --interval 300
```

#### Cluster-Specific Balancing
```bash
vm-balancer --cluster-ids 1 3 5 --dry-run
```

### Python Module Usage

You can also use the package as a Python module:

```bash
# Using the module directly
python -m vm_balancer --help

# Or import in your code
python -c "from vm_balancer import VMBalancer; print('Available')"
```

### Configuration File

The balancer looks for configuration in the following order:
1. Command line arguments
2. Environment variables
3. `.env` file in current directory
4. Default values

#### Advanced Usage
```bash
# Fast balancing with multiple migrations
vm-balancer --max-migrations-per-cycle 3 --once

# Conservative balancing with exclusions
vm-balancer --exclude-source-nodes problematic-node \
            --exclude-target-nodes maintenance-node \
            --max-migrations-per-cycle 1
```

## 🧠 How It Works

### 🔍 Overload Detection
A node is considered overloaded when:
- CPU allocation ratio > threshold (default: 7:1 vCPU:pCPU)
- **OR** Memory usage > threshold (default: 70%)
- **AND** Node is not in maintenance mode
- **AND** Node is not excluded from migrations

### 🎯 Target Selection Logic

The target node selection process follows a sophisticated multi-stage algorithm:

#### Stage 1: Initial Candidate Filtering
A node qualifies as a potential target when:
- **Node State**: Not in maintenance mode
- **VM Creation**: VM creation is allowed on the node
- **VM Limits**: Under configured VM limit (if set)
- **Exclusions**: Not in the excluded target nodes list
- **CPU Capacity**: CPU load score < target threshold (default: 6.0)
- **Memory Capacity**: Memory usage < target threshold (default: 80%)

#### Stage 2: VM-Specific Compatibility Check
For each VM migration, the system verifies:
- **Resource Estimation**: VM resources won't cause node overload after migration
  - Estimated CPU ratio: `(current_cpu + vm_cpu) / total_cpu < overload_threshold`
  - Estimated memory usage: `current_memory% + (vm_memory/total_memory)*100 < overload_threshold`
- **QEMU Compatibility**: Target node QEMU version ≥ source node QEMU version
- **Live Capacity**: Real-time resource availability

#### Stage 3: Selection Priority
From compatible nodes, selection prioritizes:
1. **Lowest CPU load score** (combination of allocation ratio + VM density)
2. **Lowest memory usage percentage**
3. **First available node** meeting all criteria

#### CPU Load Score Calculation
The system uses an advanced CPU scoring algorithm:
```
cpu_load_score = allocation_ratio + (vm_density_factor * 0.5)
```
Where:
- `allocation_ratio` = allocated_vCPUs / physical_CPUs
- `vm_density_factor` = min(vm_count / physical_CPUs, 2.0)

This considers both resource allocation and management complexity.

### 🔄 VM Selection Strategy
Migration candidates must be:
- ✅ Currently running (active state)
- ✅ No mounted ISO images
- ✅ No active snapshots
- ✅ Balancer enabled for VM
- ✅ Not migrated in last hour
- ✅ **Priority**: Smaller VMs first (less disruptive)

### 🛡️ Safety Features
- **Migration Limits**: Configurable per-cycle limits prevent system overload
- **State Validation**: Pre-migration VM and node state verification
- **Recent Migration Tracking**: Prevents VM ping-ponging
- **Resource Compatibility**: QEMU version and resource requirement checks
- **Dry Run Mode**: Test strategies without actual changes

## 📊 Monitoring & Logs

All activities are logged to `vm_balancer.log` and console output.

**Log Levels:**
- **DEBUG**: Detailed node and VM analysis
- **INFO**: Migration decisions and status updates
- **WARNING**: Potential issues and skipped operations
- **ERROR**: Failures and critical problems

**Sample Log Output:**
```
2024-01-15 10:30:00 [INFO] Starting balance cycle for 3 clusters
2024-01-15 10:30:01 [INFO] Cluster 'Production' (ID: 1) - Found 2 overloaded nodes
2024-01-15 10:30:02 [INFO] Migrating VM 'web-server-01' from 'node-heavy' to 'node-light'
2024-01-15 10:30:45 [INFO] Migration completed successfully in 43 seconds
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📦 Releases

### Latest Release
Download the latest version from [GitHub Releases](https://github.com/your-username/vm_balancer/releases/latest)

### Available Packages
- **Source Code**: Complete source with all files
- **Portable Package**: Ready-to-run for Linux/Mac/Windows  
- **Windows Package**: Optimized for Windows with setup scripts

### Quick Install from Release
```bash
# Linux/Mac
wget https://github.com/DenisKoleda/vm_balancer/releases/latest/download/vm-balancer-X.X.X-portable.tar.gz
tar -xzf vm-balancer-X.X.X-portable.tar.gz
cd vm-balancer-portable && ./run.sh

# Windows: Download vm-balancer-X.X.X-windows.zip and run install.bat
```

## 🔗 Using the VM Balancer as a library allows you to integrate its functionality into your own applications or scripts

### Simple Example
```python
from vm_balancer import VMBalancer
import asyncio

async def main():
    # Create a balancer with configuration
    balancer = VMBalancer(config_path='.env', dry_run=True)

    # Perform a single balancing run
    await balancer.run_once()

if __name__ == "__main__":
    asyncio.run(main())
```

### Component Usage
```python
from vm_balancer import VMManagerAPI, TelegramNotifier

# API client
api = VMManagerAPI(
    host="https://vmmanager.example.com",
    username="admin", 
    password="password"
)

# Notifications
notifier = TelegramNotifier(
    bot_token="your_bot_token",
    chat_id="your_chat_id",
    enabled=True
)

# Get clusters
clusters = await api.get_clusters()
```

## 🔗 Related Projects

- [VMManager 6 Documentation](https://docs.vmmanager.com/)
- [VMManager API Reference](https://docs.vmmanager.com/api/)

## ⚠️ Disclaimer

This tool performs live VM migrations. Always test in a development environment first. The authors are not responsible for any data loss or service disruption.

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-username/vm_balancer/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/your-username/vm_balancer/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/your-username/vm_balancer/wiki)
- 📋 **Release Guide**: [RELEASE.md](RELEASE.md)

---

**Made with ❤️ for the VMManager community** 
