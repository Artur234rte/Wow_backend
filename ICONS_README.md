# Получение иконок подземелий и рейдов

## Обзор

Система автоматически получает иконки для подземелий (M+) и рейд боссов из официального Blizzard Battle.net API.

## Как это работает

1. **WarcraftLogs API** → получаем `journalID` для каждого encounter
2. **Blizzard Battle.net API** → используем `journalID` для получения URL иконки
3. **constant.py** → автоматически обновляется с иконками

## Настройка

### 1. Получение Blizzard API credentials

1. Перейдите на [https://develop.battle.net/](https://develop.battle.net/)
2. Войдите в свой Battle.net аккаунт
3. Создайте новое приложение (Create Client)
4. Скопируйте **Client ID** и **Client Secret**

### 2. Добавьте credentials в .env

```bash
# .env файл
BLIZZARD_CLIENT_ID=your_client_id_here
BLIZZARD_CLIENT_SECRET=your_client_secret_here
```

## Использование

### Первичное заполнение иконок

```bash
# Запустите скрипт для получения всех иконок
python fetch_icons.py
```

Скрипт:
1. Получит `journalID` для всех encounters из WarcraftLogs
2. Запросит иконки из Blizzard API
3. Автоматически обновит [constant.py](app/agregator/constant.py)

**Время выполнения:** ~2-3 минуты (из-за rate limiting)

### Обновление отдельных иконок

Если нужно обновить только некоторые иконки, отредактируйте `fetch_icons.py` и раскомментируйте нужные ID.

## Структура данных

### До (старый формат):
```python
ENCOUNTERS = {
    62660: "Ara-Kara, City of Echoes",
    # ...
}
```

### После (новый формат):
```python
ENCOUNTERS = {
    62660: {
        "name": "Ara-Kara, City of Echoes",
        "icon": "https://render.worldofwarcraft.com/us/npcs/zoom/creature-display-119394.jpg",
        "journal_id": 1182
    },
    # ...
}
```

## API для работы с encounters

Используйте helper функции из [encounter_utils.py](app/agregator/encounter_utils.py):

```python
from app.agregator.encounter_utils import (
    get_encounter_name,
    get_encounter_icon,
    get_encounter_data,
    get_all_encounters_data,
    get_all_raids_data
)

# Получить имя
name = get_encounter_name(62660)  # "Ara-Kara, City of Echoes"

# Получить иконку
icon = get_encounter_icon(62660)  # "https://..."

# Получить все данные
data = get_encounter_data(62660)
# {
#   "id": 62660,
#   "name": "Ara-Kara, City of Echoes",
#   "icon": "https://...",
#   "journal_id": 1182
# }

# Получить все M+ подземелья
all_dungeons = get_all_encounters_data()

# Получить всех рейд боссов
all_raids = get_all_raids_data()
```

## Формат ответа для фронтенда

Для API эндпоинта используйте `get_all_encounters_data()` или `get_all_raids_data()`:

```json
[
  {
    "id": 62660,
    "name": "Ara-Kara, City of Echoes",
    "icon": "https://render.worldofwarcraft.com/us/npcs/zoom/creature-display-119394.jpg"
  },
  {
    "id": 12830,
    "name": "Eco-Dome Al'dani",
    "icon": "https://..."
  }
]
```

## Модули

### [blizzard_api.py](app/agregator/blizzard_api.py)
Модуль для работы с Blizzard Battle.net API:
- `get_blizzard_access_token()` - получение OAuth токена
- `get_journal_encounter_icon(journal_id)` - получение иконки encounter
- `get_journal_instance_icon(instance_id)` - получение иконки подземелья

### [encounter_utils.py](app/agregator/encounter_utils.py)
Утилиты для работы с encounters:
- Обратная совместимость со старым форматом
- Удобные helper функции
- Проверка типа encounter (raid/M+)

### [fetch_icons.py](fetch_icons.py)
Скрипт для первичного заполнения иконок:
- Получает journalID из WarcraftLogs
- Получает иконки из Blizzard API
- Обновляет constant.py

## Troubleshooting

### "BLIZZARD_CLIENT_ID не установлен"

Убедитесь, что вы добавили credentials в `.env` файл:
```bash
BLIZZARD_CLIENT_ID=abc123...
BLIZZARD_CLIENT_SECRET=xyz789...
```

### "HTTP 401 Unauthorized"

Проверьте, что ваши credentials правильные:
```bash
# Тест Blizzard API
python -c "from app.agregator.blizzard_api import test_blizzard_api; import asyncio; asyncio.run(test_blizzard_api())"
```

### "Иконка не найдена для журнала"

Некоторые старые encounters могут не иметь иконок в Blizzard API. Это нормально - в таком случае `icon` будет `None`.

### Rate Limiting

Скрипт автоматически добавляет задержки между запросами:
- 300ms между WarcraftLogs запросами
- 500ms между Blizzard API запросами

Если получаете 429 ошибки, увеличьте задержки в `fetch_icons.py`.

## Полезные ссылки

- [Blizzard Developer Portal](https://develop.battle.net/)
- [Battle.net OAuth](https://develop.battle.net/documentation/guides/using-oauth)
- [WoW Game Data APIs](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis)
- [WarcraftLogs API](https://www.warcraftlogs.com/api/docs)
