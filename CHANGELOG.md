# Changelog

All notable changes to the VMManager 6 Auto-Balancer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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