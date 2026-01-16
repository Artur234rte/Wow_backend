# Руководство по работе с Alembic миграциями

## Установка Alembic

```bash
# В вашем виртуальном окружении
pip install alembic
```

Alembic уже добавлен в [requirements.txt:1](requirements.txt#L1).

## Структура проекта

```
B/
├── alembic/              # Директория Alembic
│   ├── versions/         # Миграции хранятся здесь
│   ├── env.py           # Конфигурация окружения для миграций
│   └── script.py.mako   # Шаблон для новых миграций
├── alembic.ini          # Основной конфигурационный файл Alembic
└── app/
    └── models/
        └── model.py     # Ваши SQLAlchemy модели
```

## Основные команды

### 1. Создание новой миграции (автогенерация)

```bash
# Автоматически создает миграцию на основе изменений в моделях
alembic revision --autogenerate -m "описание изменений"

# Например:
alembic revision --autogenerate -m "add user table"
alembic revision --autogenerate -m "add email column to user"
```

### 2. Создание пустой миграции (ручная)

```bash
# Если нужно написать миграцию вручную
alembic revision -m "описание изменений"
```

### 3. Применение миграций

```bash
# Применить все непримененные миграции
alembic upgrade head

# Применить конкретную миграцию
alembic upgrade <revision_id>

# Применить следующую миграцию
alembic upgrade +1
```

### 4. Откат миграций

```bash
# Откатить последнюю миграцию
alembic downgrade -1

# Откатить до конкретной ревизии
alembic downgrade <revision_id>

# Откатить все миграции
alembic downgrade base
```

### 5. Просмотр истории миграций

```bash
# Показать текущую ревизию
alembic current

# Показать историю миграций
alembic history

# Показать подробную историю с информацией
alembic history --verbose
```

## Пример: Создание первой миграции

### Шаг 1: Создаем начальную миграцию

```bash
alembic revision --autogenerate -m "initial migration"
```

### Шаг 2: Проверяем созданный файл

Alembic создаст файл в `alembic/versions/` с именем вроде `abc123_initial_migration.py`.

Откройте его и проверьте, что все изменения корректны.

### Шаг 3: Применяем миграцию

```bash
alembic upgrade head
```

## Пример: Изменение существующей модели

### Ситуация: Нужно добавить новое поле в модель

1. Изменяем модель в [model.py](app/models/model.py):

```python
class MetaBySpec(Base):
    __tablename__ = "meta_by_spec"
    # ... существующие поля ...

    # Добавляем новое поле
    new_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

2. Создаем миграцию:

```bash
alembic revision --autogenerate -m "add new_field to meta_by_spec"
```

3. Проверяем созданную миграцию в `alembic/versions/`

4. Применяем:

```bash
alembic upgrade head
```

## Текущее состояние проекта

Вы **уже исправили** модель, изменив поле `key` с `nullable=True` на `nullable=False` и изменив значение для рейдов с `None` на `"raid"`.

### Что нужно сделать после пересоздания базы:

1. Убедитесь, что база данных полностью очищена
2. Создайте начальную миграцию:

```bash
alembic revision --autogenerate -m "initial schema with fixed key field"
```

3. Примените миграцию:

```bash
alembic upgrade head
```

## Важные замечания

1. **Всегда проверяйте автогенерированные миграции** перед применением. Alembic может не распознать некоторые изменения.

2. **Не редактируйте примененные миграции**. Если нужно что-то исправить, создайте новую миграцию.

3. **Backup базы данных** перед применением миграций в продакшене.

4. **Тестируйте миграции** на локальной/тестовой базе перед продакшеном.

5. **Порядок важен**: Если несколько человек работают над проектом, координируйте порядок применения миграций.

## Troubleshooting

### Alembic не видит изменения в моделях

```bash
# Проверьте, что env.py правильно импортирует Base
# Проверьте, что все модели импортируются в env.py
```

### Конфликты миграций

```bash
# Посмотрите текущую ревизию
alembic current

# Посмотрите историю
alembic history

# Если нужно объединить ветки:
alembic merge <rev1> <rev2> -m "merge migrations"
```

### База данных не синхронизирована

```bash
# Если база уже создана вручную, можно пометить текущую миграцию как примененную:
alembic stamp head
```

## Полезные ссылки

- [Официальная документация Alembic](https://alembic.sqlalchemy.org/)
- [Autogenerate в Alembic](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [Cookbook с примерами](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
