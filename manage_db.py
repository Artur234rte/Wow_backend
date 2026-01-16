#!/usr/bin/env python3
"""
Скрипт для управления базой данных и миграциями

Использование:
    python manage_db.py migrate "описание изменений"  # Создать новую миграцию
    python manage_db.py upgrade                        # Применить все миграции
    python manage_db.py downgrade                      # Откатить последнюю миграцию
    python manage_db.py current                        # Показать текущую версию
    python manage_db.py history                        # Показать историю миграций
"""

import sys
import subprocess


def run_command(cmd: list[str]) -> int:
    """Запускает команду и возвращает код возврата"""
    print(f"Выполняем: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "migrate":
        if len(sys.argv) < 3:
            print("Ошибка: Укажите описание миграции")
            print('Пример: python manage_db.py migrate "add new field"')
            sys.exit(1)
        message = sys.argv[2]
        return run_command(["alembic", "revision", "--autogenerate", "-m", message])

    elif command == "upgrade":
        return run_command(["alembic", "upgrade", "head"])

    elif command == "downgrade":
        steps = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return run_command(["alembic", "downgrade", steps])

    elif command == "current":
        return run_command(["alembic", "current"])

    elif command == "history":
        return run_command(["alembic", "history", "--verbose"])

    elif command == "stamp":
        if len(sys.argv) < 3:
            print("Ошибка: Укажите версию для stamp")
            print('Пример: python manage_db.py stamp head')
            sys.exit(1)
        revision = sys.argv[2]
        return run_command(["alembic", "stamp", revision])

    else:
        print(f"Неизвестная команда: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
