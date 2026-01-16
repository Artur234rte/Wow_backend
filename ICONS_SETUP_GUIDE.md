# Руководство по настройке иконок для подземелий и рейдов

## 🎯 Что было сделано

Добавлена полная интеграция с Blizzard Battle.net API для автоматического получения иконок подземелий и рейд боссов.

## 📋 Созданные файлы

### Основные модули
1. **[app/agregator/blizzard_api.py](app/agregator/blizzard_api.py)** - работа с Blizzard API
2. **[app/agregator/encounter_utils.py](app/agregator/encounter_utils.py)** - утилиты для работы с encounters
3. **[fetch_icons.py](fetch_icons.py)** - скрипт для заполнения иконок

### Обновленные файлы
1. **[app/agregator/quieres.py](app/agregator/quieres.py)** - добавлен запрос `QUERY_GET_JOURNAL_ID`
2. **[app/schemas/encounter_schema.py](app/schemas/encounter_schema.py)** - добавлено поле `icon`
3. **[app/main.py](app/main.py)** - обновлены эндпоинты `/meta/encounters_id/` и `/meta/raids_id/`

### Документация
1. **[ICONS_README.md](ICONS_README.md)** - подробная документация
2. **[.env.example](.env.example)** - пример конфигурации

## 🚀 Быстрый старт

### Шаг 1: Получите Blizzard API credentials

1. Перейдите на https://develop.battle.net/
2. Войдите в Battle.net аккаунт
3. Создайте приложение (Create Client)
4. Скопируйте Client ID и Client Secret

### Шаг 2: Добавьте credentials в .env

```bash
# .env
BLIZZARD_CLIENT_ID=your_client_id_here
BLIZZARD_CLIENT_SECRET=your_client_secret_here
```

### Шаг 3: Запустите скрипт получения иконок

```bash
python fetch_icons.py
```

Скрипт автоматически:
- ✅ Получит `journalID` из WarcraftLogs для каждого encounter
- ✅ Запросит URL иконок из Blizzard API
- ✅ Обновит [constant.py](app/agregator/constant.py) с новыми данными

**Время выполнения:** ~2-3 минуты

### Шаг 4: Проверьте результат

```bash
# Запустите API сервер
uvicorn app.main:app --reload

# Проверьте эндпоинты
curl http://localhost:8000/meta/encounters_id/
curl http://localhost:8000/meta/raids_id/
```

## 📊 Формат данных

### ENCOUNTERS и RAID (constant.py)

**Было:**
```python
ENCOUNTERS = {
    62660: "Ara-Kara, City of Echoes"
}
```

**Стало:**
```python
ENCOUNTERS = {
    62660: {
        "name": "Ara-Kara, City of Echoes",
        "icon": "https://render.worldofwarcraft.com/us/npcs/zoom/creature-display-119394.jpg",
        "journal_id": 1182
    }
}
```

### API Response

**GET /meta/encounters_id/**
```json
{
  "name": "Mythic+ Season 3",
  "encounters": [
    {
      "id": 62660,
      "name": "Ara-Kara, City of Echoes",
      "icon": "https://render.worldofwarcraft.com/us/npcs/zoom/creature-display-119394.jpg"
    }
  ]
}
```

**GET /meta/raids_id/**
```json
{
  "name": "Nerub-ar Palace",
  "encounters": [
    {
      "id": 2902,
      "name": "Ulgrax the Devourer",
      "icon": "https://..."
    }
  ]
}
```

## 🔧 Helper функции

Используйте из [encounter_utils.py](app/agregator/encounter_utils.py):

```python
from app.agregator.encounter_utils import (
    get_encounter_name,      # Получить имя
    get_encounter_icon,      # Получить иконку
    get_encounter_data,      # Получить все данные
    get_all_encounters_data, # Все M+ подземелья
    get_all_raids_data,      # Все рейд боссы
    is_raid,                 # Проверка на рейд
    is_mythic_plus           # Проверка на M+
)
```

## ⚠️ Важные замечания

### 1. Обратная совместимость

Модуль `encounter_utils.py` обеспечивает обратную совместимость. Даже если в `constant.py` останется старый формат (строка вместо словаря), функции будут работать корректно.

### 2. Обязательность иконок

В схеме `EncounterResponse` поле `icon` является **обязательным** (не Optional). Убедитесь, что все encounters имеют иконки после запуска `fetch_icons.py`.

### 3. Rate Limiting

Скрипт `fetch_icons.py` автоматически добавляет задержки:
- 300ms между WarcraftLogs запросами
- 500ms между Blizzard API запросами

### 4. Структура constant.py

После первого запуска `fetch_icons.py` файл `constant.py` будет обновлен. **Не редактируйте его вручную** - используйте скрипт для обновления.

## 🔄 Обновление иконок

Если нужно обновить иконки (например, в новом сезоне):

```bash
# Просто запустите скрипт снова
python fetch_icons.py
```

Скрипт перезапишет существующие данные новыми.

## 📚 Дополнительная документация

- [ICONS_README.md](ICONS_README.md) - подробная документация
- [app/agregator/blizzard_api.py](app/agregator/blizzard_api.py) - код модуля с комментариями
- [Blizzard Developer Portal](https://develop.battle.net/)

## 🐛 Troubleshooting

### Ошибка "BLIZZARD_CLIENT_ID не установлен"
→ Добавьте credentials в `.env`

### Ошибка "HTTP 401 Unauthorized"
→ Проверьте правильность credentials

### Иконка None после fetch_icons.py
→ Некоторые старые encounters могут не иметь иконок в Blizzard API (нормально)

### Rate Limiting (429 ошибки)
→ Увеличьте задержки в `fetch_icons.py` (строки с `asyncio.sleep`)

## ✅ Чек-лист для деплоя

- [ ] Получены Blizzard API credentials
- [ ] Credentials добавлены в .env (локально и на Railway)
- [ ] Запущен `fetch_icons.py` и constant.py обновлен
- [ ] Проверены эндпоинты локально
- [ ] Закоммичен обновленный constant.py
- [ ] Задеплоен на Railway
- [ ] Проверены эндпоинты в production

---

**Готово! 🎉** Теперь ваши API эндпоинты возвращают иконки для подземелий и рейдов.
