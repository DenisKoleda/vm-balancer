"""
Главная точка входа для VM Balancer
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from . import VMBalancer, __version__
from .utils.i18n import set_locale, t

# Добавляем корневую директорию проекта в путь Python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Главная функция для запуска VM Balancer"""
    # Поддержка переменной окружения для языка
    if "VM_BALANCER_LANG" in os.environ:
        set_locale(os.environ["VM_BALANCER_LANG"])

    parser = argparse.ArgumentParser(
        description=t("cli_description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{t('cli_examples')}
  vm-balancer                           {t('cli_example_default')}
  vm-balancer --dry-run                 {t('cli_example_dry_run')}
  vm-balancer --interval 600            {t('cli_example_interval')}
  vm-balancer --cluster-ids 1,2,3       {t('cli_example_clusters')}
  vm-balancer --once                    {t('cli_example_once')}
  vm-balancer --config /path/to/.env    {t('cli_example_config')}
        """,
    )

    parser.add_argument("--config", type=str, default=".env", help=t("cli_config_help"))

    parser.add_argument("--dry-run", action="store_true", help=t("cli_dry_run_help"))

    parser.add_argument("--once", action="store_true", help=t("cli_once_help"))

    parser.add_argument("--interval", type=int, help=t("cli_interval_help"))

    parser.add_argument("--cluster-ids", type=str, help=t("cli_cluster_ids_help"))

    parser.add_argument(
        "--version", action="version", version=f"VM Balancer {__version__}"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help=t("cli_verbose_help")
    )

    args = parser.parse_args()

    # Проверяем наличие файла конфигурации
    if not os.path.exists(args.config):
        print(f"❌ {t('error_config_load', error=f'File {args.config} not found')}")
        print(f"💡 Create {args.config} based on config.env.example")
        print(f"   cp config.env.example {args.config}")
        return 1

    try:
        # Создаем балансировщик
        balancer = VMBalancer(
            config_path=args.config, dry_run=args.dry_run, verbose=args.verbose
        )

        # Переопределяем параметры из командной строки
        if args.interval:
            balancer.balance_interval = args.interval

        if args.cluster_ids:
            cluster_ids = [int(x.strip()) for x in args.cluster_ids.split(",")]
            balancer.cluster_ids = cluster_ids

        print(f"🚀 {t('balancer_starting')}...")
        print(f"📁 Configuration: {args.config}")
        print(
            f"🔄 Mode: {t('balancer_dry_run_mode') if args.dry_run else 'Production'}"
        )

        if args.once:
            print(f"⚡ {t('balancer_once_mode')}")
            asyncio.run(balancer.run_once())
        else:
            print(
                f"🔄 {t('balancer_interval_mode', interval=balancer.balance_interval)}"
            )
            print("🛑 Press Ctrl+C to stop")
            asyncio.run(balancer.run())

    except KeyboardInterrupt:
        print(f"\n🛑 {t('balancer_stopping')}...")
        return 0
    except Exception as e:
        print(f"❌ {t('error_config_load', error=str(e))}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
