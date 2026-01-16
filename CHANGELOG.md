# Changelog

## 2026-01-16 - Исправление дублирования рейдов и добавление Alembic

### Исправлена проблема с дублированием рейдов

**Проблема:**
- При повторной агрегации данных рейды дублировались в базе данных
- Причина: поле `key` было `NULL` для рейдов, а в PostgreSQL `NULL != NULL`
- Уникальный индекс `UniqueConstraint('class_name', 'spec', 'encounter_id', 'key')` не работал для записей с `NULL`

**Решение:**
- Изменено поле `key` в модели `MetaBySpec`: теперь `nullable=False` ([model.py:24](app/models/model.py#L24))
- Изменена логика в `fetch_single_spec_meta`: для рейдов используется значение `"raid"` вместо `None` ([view.py:644](app/agregator/view.py#L644))
- Теперь значения поля `key`:
  - M+ low keys: `"low"`
  - M+ high keys: `"high"`
  - Рейды: `"raid"`

**Результат:**
- При повторной агрегации данные корректно обновляются через `INSERT ON CONFLICT DO UPDATE`
- Дубликаты больше не создаются

### Добавлена поддержка Alembic для миграций

**Создана инфраструктура:**
- `alembic.ini` - конфигурация Alembic
- `alembic/env.py` - конфигурация окружения для миграций с поддержкой async
- `alembic/script.py.mako` - шаблон для новых миграций
- `alembic/versions/` - директория для миграций
- `alembic/versions/001_initial_schema.py.example` - пример начальной миграции

**Документация:**
- `MIGRATIONS_README.md` - подробное руководство по работе с Alembic
- `QUICKSTART_ALEMBIC.md` - быстрый старт для нового проекта
- `manage_db.py` - вспомогательный скрипт для управления миграциями

**Обновлены зависимости:**
- Добавлен `alembic==1.15.2` в `requirements.txt`

### Основные команды Alembic

```bash
# Создать миграцию
alembic revision --autogenerate -m "описание"
# или через скрипт:
python manage_db.py migrate "описание"

# Применить миграции
alembic upgrade head
# или:
python manage_db.py upgrade

# Откатить миграцию
alembic downgrade -1
# или:
python manage_db.py downgrade

# Посмотреть статус
alembic current
python manage_db.py current

# История
alembic history --verbose
python manage_db.py history
```

### Инструкции для применения изменений

После полного пересоздания базы данных:

1. Установите Alembic: `pip install alembic`
2. Создайте начальную миграцию: `alembic revision --autogenerate -m "initial schema"`
3. Примените миграцию: `alembic upgrade head`
4. Запустите агрегацию: `python -m app.agregator.view`

### Измененные файлы

- `app/models/model.py` - изменено поле `key` (nullable=False)
- `app/agregator/view.py` - изменена логика заполнения `key` для рейдов
- `app/agregator/constant.py` - раскомментированы ENCOUNTERS (для M+)
- `requirements.txt` - добавлен alembic
- Новые файлы:
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/script.py.mako`
  - `alembic/versions/001_initial_schema.py.example`
  - `MIGRATIONS_README.md`
  - `QUICKSTART_ALEMBIC.md`
  - `manage_db.py`
  - `CHANGELOG.md` (этот файл)
