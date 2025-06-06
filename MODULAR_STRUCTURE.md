# VM Balancer - Modular Structure Guide

## ✅ Restructuring Complete

The VM Balancer project has been successfully transformed from a monolithic script into a modular Python library following development best practices.

## 📦 Final Package Structure

```
vm-balancer/
├── src/vm_balancer/          # Main package
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # Module execution (python -m vm_balancer)
│   ├── main.py               # main() function for CLI
│   ├── api/                  # VMManager API client
│   │   ├── __init__.py
│   │   └── client.py         # VMManagerAPI
│   ├── core/                 # Core balancing logic
│   │   ├── __init__.py
│   │   └── balancer.py       # VMBalancer
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   ├── cluster.py        # ClusterInfo
│   │   ├── node.py           # NodeInfo
│   │   └── vm.py             # VMInfo
│   ├── monitoring/           # Node monitoring
│   │   ├── __init__.py
│   │   └── ssh.py            # SSHMonitor
│   ├── notifications/        # Notifications
│   │   ├── __init__.py
│   │   └── telegram.py       # TelegramNotifier
│   └── utils/                # Utilities
│       ├── __init__.py
│       └── env.py            # EnvConfig
├── pyproject.toml            # Modern package configuration
├── setup.py                  # Compatibility with older versions
├── MANIFEST.in               # Include additional files
├── requirements.txt          # Production dependencies
├── config.env.example        # Configuration example
└── MODULAR_STRUCTURE.md      # This file
```

## 🚀 Usage Methods

### 1. Console Command (Recommended)
```bash
# Install package
pip install vm-balancer

# Or install from sources
pip install .

# Usage
vm-balancer --help
vm-balancer --config .env --dry-run --once
vm-balancer --interval 300 --cluster-ids 1,2,3
```

### 2. Module Execution
```bash
python -m vm_balancer --help
python -m vm_balancer --config .env --dry-run --once
```

## 📋 Development Imports

```python
# Main balancer class
from vm_balancer import VMBalancer

# API client
from vm_balancer import VMManagerAPI

# Data models
from vm_balancer import ClusterInfo, NodeInfo, VMInfo

# Components
from vm_balancer import TelegramNotifier, SSHMonitor

# Usage example
balancer = VMBalancer(config_path='.env', dry_run=True)
await balancer.run_once()
```

## 🔧 Configuration

Use `config.env.example` file as a template for configuration:

```bash
# Copy and configure
cp config.env.example .env
# Edit connection settings
nano .env
```

## ✅ Preserved Functionality

All original monolithic script capabilities are preserved:

- ✅ Automatic VM balancing
- ✅ SSH node monitoring
- ✅ Telegram notifications
- ✅ Dry-run mode
- ✅ Node exclusions
- ✅ Threshold configuration
- ✅ Migration limits
- ✅ History tracking
- ✅ QEMU compatibility

## 🎁 Improvements

### Modularity
- Clear separation of responsibilities
- Easy component testing
- Import into other projects

### Development Convenience
- Type-safe configuration
- vm-balancer console command
- python -m vm_balancer module execution
- Modern build tools

### Standardization
- PEP 8 compliance
- Standard Python package structure
- Documented exports

## 🔄 Migration from Old Code

1. **Replace direct script calls:**
   ```bash
   # Old way
   python vm_balancer.py --dry-run --once
   
   # New way
   vm-balancer --dry-run --once
   ```

2. **Update instance creation:**
   ```python
   # Old way
   api = VMManagerAPI(host, user, pass)
   balancer = VMBalancer(api, dry_run=True, ...)
   
   # New way
   balancer = VMBalancer(config_path='.env', dry_run=True)
   ```

## 🧪 Testing

```bash
# Check imports
python -c "from vm_balancer import *; print('OK')"

# Check CLI
vm-balancer --version

# Check module execution  
python -m vm_balancer --version

# Simulation with config
vm-balancer --config .env --dry-run --once --verbose
```
