"""
Environment configuration utilities
"""

import json
import os
from typing import List

from dotenv import load_dotenv


def get_env_value(key: str, default: str = "") -> str:
    """Get environment variable value, removing comments"""
    value = os.getenv(key, default)
    # Remove comments from environment variables
    if "#" in value:
        value = value.split("#")[0].strip()
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


def get_env_list(key: str, default: str = "") -> List[str]:
    """Get environment variable as list, removing comments and filtering empty values"""
    value = get_env_value(key, default)
    if not value:
        return []
    # Split by comma and filter out empty strings
    return [item.strip() for item in value.split(",") if item.strip()]


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean"""
    value = get_env_value(key, str(default).lower())
    return value.lower() in ("true", "1", "yes", "on")


class EnvConfig:
    """Configuration loader from environment file"""

    def __init__(self, config_path: str = ".env"):
        """Load configuration from file"""
        if os.path.exists(config_path):
            load_dotenv(config_path)

        # VMManager connection settings
        self.vmmanager_host = get_env_value("VMMANAGER_HOST", "https://localhost")
        self.vmmanager_username = get_env_value("VMMANAGER_USERNAME", "admin")
        self.vmmanager_password = get_env_value("VMMANAGER_PASSWORD", "")

        # Balance settings
        self.balance_interval = get_env_int("BALANCE_INTERVAL", 600)
        self.cluster_ids = get_env_list("CLUSTER_IDS")
        self.max_migrations_per_cycle = get_env_int("MAX_MIGRATIONS_PER_CYCLE", 1)
        self.migration_timeout = get_env_int("MIGRATION_TIMEOUT", 1800)

        # Thresholds
        self.cpu_overload_threshold = get_env_float("CPU_OVERLOAD_THRESHOLD", 7.0)
        self.memory_overload_threshold = get_env_float(
            "MEMORY_OVERLOAD_THRESHOLD", 70.0
        )
        self.cpu_target_threshold = get_env_float("CPU_TARGET_THRESHOLD", 6.0)
        self.memory_target_threshold = get_env_float("MEMORY_TARGET_THRESHOLD", 80.0)

        # Node exclusions
        self.exclude_source_nodes = get_env_list("EXCLUDE_SOURCE_NODES")
        self.exclude_target_nodes = get_env_list("EXCLUDE_TARGET_NODES")

        # Logging
        self.log_level = get_env_value("LOG_LEVEL", "INFO")

        # SSL verification
        self.verify_ssl = get_env_bool("VERIFY_SSL", True)

        # SSH monitoring
        self.ssh_enabled = get_env_bool("SSH_ENABLED", False)
        self.ssh_username = get_env_value("SSH_USERNAME", "")
        self.ssh_private_key_path = get_env_value("SSH_PRIVATE_KEY_PATH", "")
        self.ssh_password = get_env_value("SSH_PASSWORD", "")
        self.ssh_timeout = get_env_int("SSH_TIMEOUT", 10)

        # SSH hosts mapping (JSON format)
        ssh_mapping_str = get_env_value("SSH_HOSTS_MAPPING", "{}")
        try:
            self.ssh_hosts_mapping = (
                json.loads(ssh_mapping_str) if ssh_mapping_str else {}
            )
        except json.JSONDecodeError:
            self.ssh_hosts_mapping = {}

        # Telegram notifications
        self.telegram_bot_token = get_env_value("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = get_env_value("TELEGRAM_CHAT_ID", "")
