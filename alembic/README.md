# Alembic Migrations Directory

Эта директория содержит миграции базы данных для проекта WoW Aggregator.

## Структура

```
alembic/
├── versions/                          # Все миграции хранятся здесь
│   └── 001_initial_schema.py.example # Пример начальной миграции
├── env.py                            # Конфигурация окружения (async поддержка)
├── script.py.mako                    # Шаблон для новых миграций
└── README.md                         # Этот файл
```

## Быстрый старт

### 1. Создать миграцию

```bash
# Из корневой директории проекта
alembic revision --autogenerate -m "описание изменений"

# Или через скрипт-помощник
python manage_db.py migrate "описание изменений"
```

### 2. Применить миграции

```bash
alembic upgrade head

# Или через скрипт
python manage_db.py upgrade
```

### 3. Откатить миграцию

```bash
alembic downgrade -1

# Или через скрипт
python manage_db.py downgrade
```

## Versions Directory

Все файлы миграций создаются в директории `versions/`. Формат имени:

```
<revision_id>_<slug>.py
```

Например:
- `abc123def456_add_user_table.py`
- `xyz789_update_meta_by_spec.py`

## Пример миграции

В директории `versions/` есть файл `001_initial_schema.py.example` - это пример начальной миграции, которая создает таблицу `meta_by_spec` с исправленным полем `key`.

**Как использовать:**
1. После пересоздания БД удалите суффикс `.example`
2. Или создайте свою миграцию через `alembic revision --autogenerate`

## Подробная документация

Смотрите:
- [QUICKSTART_ALEMBIC.md](../QUICKSTART_ALEMBIC.md) - быстрый старт
- [MIGRATIONS_README.md](../MIGRATIONS_README.md) - подробное руководство
- [CHANGELOG.md](../CHANGELOG.md) - история изменений

## Важно

- Не редактируйте примененные миграции
- Всегда проверяйте автогенерированный код перед применением
- Делайте backup БД перед применением миграций в продакшене
