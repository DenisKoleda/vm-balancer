# Changelog

All notable changes to the VMManager 6 Auto-Balancer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-06-06

### 🎯 Major Restructuring - Modular Architecture

#### Added
- **Modular Package Structure**: Complete restructuring from monolithic script to professional Python package
- **Console Command**: New `vm-balancer` command-line interface after installation
- **Python Module Support**: Can be run as `python -m vm_balancer`
- **Library Import Support**: Can be imported and used as a library in other projects
- **Type-Safe Configuration**: New `EnvConfig` class with proper type parsing
- **Modern Packaging**: Added `pyproject.toml` and modern Python packaging standards
- **Clean Package Structure**: Organized into logical subpackages (api, core, models, monitoring, notifications, utils)

#### Changed
- **BREAKING**: Constructor signature changed for `VMBalancer` class (now takes `config_path` instead of separate parameters)
- **BREAKING**: Package import structure - all classes now available from main package
- **Entry Points**: New console script entry point replaces direct script execution
- **Configuration Loading**: Simplified configuration loading via `EnvConfig` class
- **Installation Method**: Now installable via `pip install .` or `pip install vm-balancer`

#### Improved
- **Code Organization**: Clear separation of concerns across modules
- **Developer Experience**: Easy imports, clean API, proper type hints
- **Testing Ready**: Modular structure enables comprehensive unit testing
- **Documentation**: Updated documentation for new modular structure

#### Migration Guide
```bash
# Old way
python vm_balancer.py --dry-run --once

# New way
vm-balancer --dry-run --once
# or
python -m vm_balancer --dry-run --once
```

### Module Structure
```
src/vm_balancer/
├── api/client.py          # VMManagerAPI
├── core/balancer.py       # VMBalancer main logic
├── models/               # Data models (VMInfo, NodeInfo, ClusterInfo)
├── monitoring/ssh.py      # SSHMonitor
├── notifications/telegram.py  # TelegramNotifier
└── utils/env.py          # EnvConfig
```

## [1.0.0] - 2025-06-03

### Added
- Automatic VM load balancing for VMManager 6
- Interactive console interface with rich UI
- Configurable CPU and memory thresholds
- Cluster filtering and node exclusion options
- Dry run mode for safe testing
- Comprehensive logging system
- Migration limits per cycle for controlled balancing
- Safety checks for VM constraints and node states
- Support for environment variables and command line arguments
- QEMU version compatibility checks
- Recent migration tracking to prevent ping-ponging
- Support for migration timeout
- Initial public release
- Complete project documentation
- MIT license

### Features
- Smart VM selection algorithm (prioritizes smaller VMs)
- Real-time cluster and node status monitoring
- Automatic detection of overloaded and underloaded nodes
- Support for maintenance mode and VM creation restrictions
- Configurable migration timeouts
- SSL certificate verification options
- Detailed error handling and recovery

### Security
- Secure credential management
- SSL/TLS support for API communications
- Input validation for all configuration parameters
- Safe migration practices with rollback capabilities

---

## Version History

- **v1.0.0**: Initial stable release with core functionality
- **v0.x.x**: Development versions (internal testing) 
