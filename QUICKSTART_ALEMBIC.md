# Быстрый старт с Alembic

## После пересоздания базы данных

### Шаг 1: Установите Alembic (если еще не установлен)

```bash
pip install alembic
```

### Шаг 2: Создайте начальную миграцию

```bash
# Автогенерация миграции на основе текущих моделей
alembic revision --autogenerate -m "initial schema with fixed key field"
```

### Шаг 3: Примените миграцию

```bash
alembic upgrade head
```

### Шаг 4: Запустите агрегацию

```bash
python -m app.agregator.view
```

## Для будущих изменений модели

### 1. Измените модель в [app/models/model.py](app/models/model.py)

Например, добавьте новое поле:

```python
class MetaBySpec(Base):
    # ... существующие поля ...
    new_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### 2. Создайте миграцию

```bash
alembic revision --autogenerate -m "add new_field"
```

### 3. Проверьте миграцию

Откройте созданный файл в `alembic/versions/` и убедитесь, что все изменения корректны.

### 4. Примените миграцию

```bash
alembic upgrade head
```

## Полезные команды

```bash
# Посмотреть текущую версию БД
alembic current

# Посмотреть историю миграций
alembic history

# Откатить последнюю миграцию
alembic downgrade -1

# Откатить все миграции
alembic downgrade base
```

## Что было исправлено

**Проблема:** Рейды дублировались при повторной агрегации, потому что поле `key` было `NULL` для рейдов, а PostgreSQL считает `NULL != NULL`.

**Решение:**
- Изменили модель: `key` теперь `nullable=False`
- Для M+ low keys: `key = "low"`
- Для M+ high keys: `key = "high"`
- Для рейдов: `key = "raid"` (вместо `None`)

Теперь уникальный индекс работает корректно, и при повторной агрегации данные **обновляются** вместо дублирования.

## Подробная документация

Смотрите [MIGRATIONS_README.md](MIGRATIONS_README.md) для полного руководства.
