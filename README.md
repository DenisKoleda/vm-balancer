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

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
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

### Interactive Mode (Recommended)

Launch the rich console interface:

```bash
python interactive.py
```

**Interactive features:**
- 🌈 Beautiful console interface with real-time updates
- 🔐 Secure credential management and connection testing
- 📊 Live cluster and node status monitoring
- ⚙️ Dynamic configuration adjustment
- 🚀 One-click balancing execution
- 📝 Real-time log streaming
- 🧪 Easy dry-run mode toggle

### Command Line Mode

#### First Run (Recommended)
```bash
# Test without making changes
python vm_balancer.py --dry-run --once --log-level DEBUG
```

#### Single Balancing Run
```bash
python vm_balancer.py --once
```

#### Continuous Monitoring
```bash
python vm_balancer.py --interval 300
```

#### Cluster-Specific Balancing
```bash
python vm_balancer.py --cluster-ids 1 3 5 --dry-run
```

#### Advanced Usage
```bash
# Fast balancing with multiple migrations
python vm_balancer.py --max-migrations-per-cycle 3 --once

# Conservative balancing with exclusions
python vm_balancer.py --exclude-source-nodes problematic-node \
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

### 🎯 Target Selection
A node can accept VMs when:
- CPU allocation ratio < threshold (default: 6:1 vCPU:pCPU)
- **AND** Memory usage < threshold (default: 80%)
- **AND** Not in maintenance mode
- **AND** VM creation is allowed
- **AND** Under VM limit (if set)
- **AND** Not excluded as target

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

## 🔗 Related Projects

- [VMManager 6 Documentation](https://docs.vmmanager.com/)
- [VMManager API Reference](https://docs.vmmanager.com/api/)

## ⚠️ Disclaimer

This tool performs live VM migrations. Always test in a development environment first. The authors are not responsible for any data loss or service disruption.

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-username/vm_balancer/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/your-username/vm_balancer/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/your-username/vm_balancer/wiki)

---

**Made with ❤️ for the VMManager community** 