"""
Internationalization support for VM Balancer
"""

import locale
import os


# Determine system locale
def get_system_locale() -> str:
    """Get system locale, defaulting to English"""
    try:
        system_locale = locale.getlocale()[0]
        if system_locale and system_locale.startswith("ru"):
            return "ru"
        return "en"
    except Exception:
        return "en"


# Current locale (can be overridden by environment variable)
CURRENT_LOCALE = os.getenv("VM_BALANCER_LANG", get_system_locale())

# Translation dictionaries
TRANSLATIONS = {
    "en": {
        # CLI messages
        "cli_description": "VM Balancer - automatic virtual machine balancing",
        "cli_config_help": "Path to configuration file (default: .env)",
        "cli_dry_run_help": "Simulation mode - analysis without migrations",
        "cli_once_help": "Perform only one check and exit",
        "cli_interval_help": (
            "Interval between checks in seconds (overrides config value)"
        ),
        "cli_cluster_ids_help": (
            "List of cluster IDs to process (overrides config value)"
        ),
        "cli_verbose_help": "Verbose output",
        "cli_examples": "Usage examples:",
        "cli_example_default": "# Run with default settings",
        "cli_example_dry_run": "# Check without performing migrations",
        "cli_example_interval": "# Check every 10 minutes",
        "cli_example_clusters": "# Process only specified clusters",
        "cli_example_once": "# Single check",
        "cli_example_config": "# Use specific configuration file",
        # Balancer messages
        "balancer_starting": "Starting VM Balancer",
        "balancer_dry_run_mode": (
            "DRY RUN MODE - no actual migrations will be performed"
        ),
        "balancer_interval_mode": (
            "Running in interval mode, checking every {interval} seconds"
        ),
        "balancer_once_mode": "Running in single-check mode",
        "balancer_stopping": "Stopping VM Balancer",
        "balancer_cycle_start": "Starting balance cycle for {count} clusters",
        "balancer_cycle_complete": "Balance cycle completed",
        "balancer_no_clusters": "No clusters found or configured",
        # Migration messages
        "migration_start": "Migrating VM {vm_name} from {source_node} to {target_node}",
        "migration_dry_run": (
            "[DRY RUN] Would migrate VM {vm_name} from {source_node} to {target_node}"
        ),
        "migration_success": "VM {vm_name} migration completed successfully",
        "migration_failed": "VM {vm_name} migration failed: {error}",
        "migration_skipped": "VM {vm_name} migration skipped: {reason}",
        # Node messages
        "node_overloaded": (
            "Node {node_name} is overloaded (CPU: {cpu_load}, Memory: {memory_usage}%)"
        ),
        "node_target_found": "Found target node {node_name} for VM migration",
        "node_no_target": "No suitable target node found for VM {vm_name}",
        "node_maintenance": "Node {node_name} is in maintenance mode, skipping",
        # Error messages
        "error_config_load": "Failed to load configuration: {error}",
        "error_api_connection": "Failed to connect to VMManager API: {error}",
        "error_cluster_load": "Failed to load cluster {cluster_id}: {error}",
        "error_vm_migrate": "Failed to migrate VM {vm_name}: {error}",
        "error_ssh_connection": "SSH connection failed for node {node_name}: {error}",
        # Success messages
        "success_config_loaded": "Configuration loaded successfully",
        "success_api_connected": "Connected to VMManager API successfully",
        "success_clusters_loaded": "Loaded {count} clusters",
        # Telegram notifications
        "telegram_enabled": "Telegram notifications enabled",
        "telegram_disabled": (
            "Telegram notifications requested but bot_token or chat_id not provided."
            " Notifications disabled."
        ),
        "telegram_send_failed": "Failed to send Telegram notification: {error}",
        "telegram_migration_started": "VM Migration Started",
        "telegram_migration_completed": "VM Migration Completed",
        "telegram_migration_failed": "VM Migration Failed",
        "telegram_balance_cycle_started": "Balance Cycle Started",
        "telegram_balance_cycle_finished": "Balance Cycle Finished",
        "telegram_vm_label": "VM:",
        "telegram_from_label": "From:",
        "telegram_to_label": "To:",
        "telegram_duration_label": "Duration: {duration:.1f} seconds",
        "telegram_error_label": "Error:",
        "telegram_clusters_label": "Clusters: {count}",
        "telegram_migrations_label": "Migrations performed: {count}",
        "telegram_time_label": "Time: {time}",
        "telegram_dry_run_mode": "DRY RUN",
        "telegram_live_mode": "LIVE",
        "telegram_completed_mode": "COMPLETED",
        # SSH monitoring
        "ssh_monitoring_warning": (
            "SSH monitoring enabled but no private key or password provided"
        ),
        "ssh_load_average_debug": (
            "SSH load average for {host}: {load_1m}, {load_5m}, {load_15m}"
        ),
        "ssh_connection_failed": "SSH connection failed for {host}:{port}: {error}",
        "ssh_load_error": "Error getting load average from {host}:{port}: {error}",
        "ssh_monitoring_started": "Starting SSH monitoring for {count} nodes",
        "ssh_monitoring_no_nodes": "No nodes available for SSH monitoring",
        "ssh_load_updated": "Updated load average for node {node}: {load}",
        "ssh_monitoring_failed": "SSH monitoring failed for node {node}",
        "ssh_monitoring_exception": "Exception monitoring node {node}: {error}",
    },
    "ru": {
        # CLI сообщения
        "cli_description": (
            "VM Balancer - автоматическая балансировка виртуальных машин"
        ),
        "cli_config_help": "Путь к файлу конфигурации (по умолчанию: .env)",
        "cli_dry_run_help": "Режим симуляции - анализ без выполнения миграций",
        "cli_once_help": "Выполнить только одну проверку и завершить работу",
        "cli_interval_help": (
            "Интервал между проверками в секундах (переопределяет значение из"
            " конфигурации)"
        ),
        "cli_cluster_ids_help": (
            "Список ID кластеров через запятую для обработки (переопределяет значение"
            " из конфигурации)"
        ),
        "cli_verbose_help": "Подробный вывод",
        "cli_examples": "Примеры использования:",
        "cli_example_default": "# Запуск с настройками по умолчанию",
        "cli_example_dry_run": "# Проверка без выполнения миграций",
        "cli_example_interval": "# Проверка каждые 10 минут",
        "cli_example_clusters": "# Обработка только указанных кластеров",
        "cli_example_once": "# Однократная проверка",
        "cli_example_config": "# Использование конкретного файла конфигурации",
        # Сообщения балансировщика
        "balancer_starting": "Запуск VM Balancer",
        "balancer_dry_run_mode": (
            "РЕЖИМ СИМУЛЯЦИИ - реальные миграции выполняться не будут"
        ),
        "balancer_interval_mode": (
            "Работа в режиме интервала, проверка каждые {interval} секунд"
        ),
        "balancer_once_mode": "Работа в режиме одной проверки",
        "balancer_stopping": "Остановка VM Balancer",
        "balancer_cycle_start": "Начало цикла балансировки для {count} кластеров",
        "balancer_cycle_complete": "Цикл балансировки завершен",
        "balancer_no_clusters": "Кластеры не найдены или не настроены",
        # Сообщения миграции
        "migration_start": "Миграция VM {vm_name} с {source_node} на {target_node}",
        "migration_dry_run": (
            "[СИМУЛЯЦИЯ] Будет выполнена миграция VM {vm_name} с {source_node} на"
            " {target_node}"
        ),
        "migration_success": "Миграция VM {vm_name} успешно завершена",
        "migration_failed": "Миграция VM {vm_name} завершилась ошибкой: {error}",
        "migration_skipped": "Миграция VM {vm_name} пропущена: {reason}",
        # Сообщения узлов
        "node_overloaded": (
            "Узел {node_name} перегружен (CPU: {cpu_load}, Память: {memory_usage}%)"
        ),
        "node_target_found": "Найден целевой узел {node_name} для миграции VM",
        "node_no_target": "Не найден подходящий целевой узел для VM {vm_name}",
        "node_maintenance": (
            "Узел {node_name} находится в режиме обслуживания, пропускаем"
        ),
        # Сообщения об ошибках
        "error_config_load": "Не удалось загрузить конфигурацию: {error}",
        "error_api_connection": "Не удалось подключиться к VMManager API: {error}",
        "error_cluster_load": "Не удалось загрузить кластер {cluster_id}: {error}",
        "error_vm_migrate": "Не удалось выполнить миграцию VM {vm_name}: {error}",
        "error_ssh_connection": "Ошибка SSH подключения к узлу {node_name}: {error}",
        # Сообщения об успехе
        "success_config_loaded": "Конфигурация успешно загружена",
        "success_api_connected": "Успешное подключение к VMManager API",
        "success_clusters_loaded": "Загружено {count} кластеров",
        # Telegram уведомления
        "telegram_enabled": "Telegram уведомления включены",
        "telegram_disabled": (
            "Запрошены Telegram уведомления, но bot_token или chat_id не предоставлены."
            " Уведомления отключены."
        ),
        "telegram_send_failed": "Не удалось отправить Telegram уведомление: {error}",
        "telegram_migration_started": "Начата миграция VM",
        "telegram_migration_completed": "Миграция VM завершена",
        "telegram_migration_failed": "Ошибка миграции VM",
        "telegram_balance_cycle_started": "Начат цикл балансировки",
        "telegram_balance_cycle_finished": "Цикл балансировки завершен",
        "telegram_vm_label": "VM:",
        "telegram_from_label": "С:",
        "telegram_to_label": "На:",
        "telegram_duration_label": "Длительность: {duration:.1f} секунд",
        "telegram_error_label": "Ошибка:",
        "telegram_clusters_label": "Кластеры: {count}",
        "telegram_migrations_label": "Выполнено миграций: {count}",
        "telegram_time_label": "Время: {time}",
        "telegram_dry_run_mode": "СИМУЛЯЦИЯ",
        "telegram_live_mode": "РЕАЛЬНЫЙ",
        "telegram_completed_mode": "ЗАВЕРШЕНО",
        # SSH мониторинг
        "ssh_monitoring_warning": (
            "SSH мониторинг включен, но не предоставлен приватный ключ или пароль"
        ),
        "ssh_load_average_debug": (
            "SSH load average для {host}: {load_1m}, {load_5m}, {load_15m}"
        ),
        "ssh_connection_failed": "Ошибка SSH соединения для {host}:{port}: {error}",
        "ssh_load_error": "Ошибка получения load average с {host}:{port}: {error}",
        "ssh_monitoring_started": "Запуск SSH мониторинга для {count} узлов",
        "ssh_monitoring_no_nodes": "Нет узлов для SSH мониторинга",
        "ssh_load_updated": "Обновлен load average для узла {node}: {load}",
        "ssh_monitoring_failed": "SSH мониторинг неудачен для узла {node}",
        "ssh_monitoring_exception": "Исключение при мониторинге узла {node}: {error}",
    },
}


def t(key: str, **kwargs) -> str:
    """
    Translate a message key with optional formatting arguments

    Args:
        key: Translation key
        **kwargs: Formatting arguments

    Returns:
        Translated and formatted string
    """
    translations = TRANSLATIONS.get(CURRENT_LOCALE, TRANSLATIONS["en"])
    message = translations.get(key, TRANSLATIONS["en"].get(key, key))

    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message

    return message


def set_locale(locale_code: str) -> None:
    """Set the current locale"""
    global CURRENT_LOCALE
    if locale_code in TRANSLATIONS:
        CURRENT_LOCALE = locale_code


def get_locale() -> str:
    """Get the current locale"""
    return CURRENT_LOCALE


def get_available_locales() -> list:
    """Get list of available locales"""
    return list(TRANSLATIONS.keys())
