"""
Telegram notification support for VM migration events
"""

import logging
from datetime import datetime
from typing import Optional

import requests

from ..utils.i18n import t


class TelegramNotifier:
    """Telegram notification support for migration events"""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        enabled: bool = False,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)

        if enabled and not (bot_token and chat_id):
            logging.warning(t("telegram_disabled"))
        elif self.enabled:
            logging.info(t("telegram_enabled"))

    def send_message(self, message: str) -> bool:
        """Send message to Telegram"""
        if not self.enabled:
            return True

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}

            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return True

        except Exception as e:
            logging.error(t("telegram_send_failed", error=str(e)))
            return False

    def notify_migration_start(
        self, vm_name: str, source_node: str, target_node: str
    ) -> None:
        """Notify about migration start"""
        message = (
            f"🔄 <b>{t('telegram_migration_started')}</b>\n\n"
            f"{t('telegram_vm_label')} <code>{vm_name}</code>\n"
            f"{t('telegram_from_label')} <code>{source_node}</code>\n"
            f"{t('telegram_to_label')} <code>{target_node}</code>\n"
            f"{t('telegram_time_label', time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        self.send_message(message)

    def notify_migration_success(
        self, vm_name: str, source_node: str, target_node: str, duration: float
    ) -> None:
        """Notify about successful migration"""
        message = (
            f"✅ <b>{t('telegram_migration_completed')}</b>\n\n"
            f"{t('telegram_vm_label')} <code>{vm_name}</code>\n"
            f"{t('telegram_from_label')} <code>{source_node}</code>\n"
            f"{t('telegram_to_label')} <code>{target_node}</code>\n"
            f"{t('telegram_duration_label', duration=duration)}\n"
            f"{t('telegram_time_label', time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        self.send_message(message)

    def notify_migration_failure(
        self, vm_name: str, source_node: str, target_node: str, error: str
    ) -> None:
        """Notify about failed migration"""
        message = (
            f"❌ <b>{t('telegram_migration_failed')}</b>\n\n"
            f"{t('telegram_vm_label')} <code>{vm_name}</code>\n"
            f"{t('telegram_from_label')} <code>{source_node}</code>\n"
            f"{t('telegram_to_label')} <code>{target_node}</code>\n"
            f"{t('telegram_error_label')} <code>{error}</code>\n"
            f"{t('telegram_time_label', time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        self.send_message(message)

    def notify_balance_cycle_start(
        self, cluster_count: int, dry_run: bool = False
    ) -> None:
        """Notify about balance cycle start"""
        mode = (
            f"🧪 {t('telegram_dry_run_mode')}"
            if dry_run
            else f"🔄 {t('telegram_live_mode')}"
        )
        message = (
            f"{mode} <b>{t('telegram_balance_cycle_started')}</b>\n\n"
            f"{t('telegram_clusters_label', count=cluster_count)}\n"
            f"{t('telegram_time_label', time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        self.send_message(message)

    def notify_balance_cycle_complete(
        self, total_migrations: int, dry_run: bool = False
    ) -> None:
        """Notify about balance cycle completion"""
        mode = (
            f"🧪 {t('telegram_dry_run_mode')}"
            if dry_run
            else f"✅ {t('telegram_completed_mode')}"
        )
        message = (
            f"{mode} <b>{t('telegram_balance_cycle_finished')}</b>\n\n"
            f"{t('telegram_migrations_label', count=total_migrations)}\n"
            f"{t('telegram_time_label', time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        self.send_message(message)
