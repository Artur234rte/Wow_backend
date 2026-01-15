# WarcraftLogs API - Полное руководство по фильтрам и параметрам

## Обзор

WarcraftLogs API предоставляет два типа рейтингов:
- **characterRankings** - рейтинги по персонажам (DPS, HPS, отдельные игроки)
- **fightRankings** - рейтинги по боям (скорость килла, execution)

## Основные параметры (общие для обоих типов)

### 1. `bracket: Int`
**Назначение:** Фильтрация по специфическому bracket (диапазону)

**Для WoW:**
- **Mythic+**: уровень ключа (2-25)
- **Raid**: item level (634-639)

**Примеры:**
```graphql
# M+: только ключи 12+
bracket: 12

# Raid: только персонажи с ilvl 638+
bracket: 638
```

**Поведение:** Работает как **минимальный порог** (>=)

---

### 2. `difficulty: Int`
**Назначение:** Фильтрация по сложности контента

**Значения для WoW Raids:**
- `3` - Normal
- `4` - Heroic
- `5` - Mythic

**Для Mythic+:** Не используется

**Примеры:**
```graphql
# Только Mythic рейд
difficulty: 5

# Только Heroic
difficulty: 4
```

---

### 3. `metric: CharacterRankingMetricType` (для characterRankings)
**Назначение:** Выбор метрики для сортировки

**Доступные метрики:**
- `playerscore` - RaiderIO score (только для Mythic+)
- `dps` - Урон в секунду
- `hps` - Хил в секунду
- `bossdps` - DPS только по боссу (без аддов)
- `tankhps` - Эффективное хиление для танков
- `krsi` - Kill Rating Survival Index

**Примеры:**
```graphql
# Mythic+
metric: playerscore

# Raid - DPS
metric: dps

# Raid - Healers
metric: hps
```

---

### 4. `metric: FightRankingMetricType` (для fightRankings)
**Назначение:** Метрика для рейтинга боев

**Доступные метрики:**
- `speed` - Скорость килла
- `execution` - Качество выполнения механик
- `feats` - Достижения

**Примеры:**
```graphql
# Самые быстрые киллы
metric: speed

# Лучшее выполнение механик
metric: execution
```

---

### 5. `filter: String`
**Назначение:** Продвинутая фильтрация (синтаксис идентичен поиску на сайте)

**Примеры фильтров:**
```graphql
# Только живые персонажи (не умершие)
filter: "death=0"

# Item level >= 638
filter: "ilvl>=638"

# Конкретный талант или абилка
filter: "ability.id=123456"

# Комбинация условий
filter: "death=0 AND ilvl>=638"

# Конкретный сервер
filter: "server.name='Tarren Mill'"
```

**Где найти синтаксис:** Используйте поиск на warcraftlogs.com, скопируйте строку фильтра

---

### 6. `page: Int`
**Назначение:** Пагинация результатов

**По умолчанию:** `page: 1`

**Примеры:**
```graphql
# Первая страница (топ-100)
page: 1

# Вторая страница (101-200)
page: 2
```

---

### 7. `partition: Int`
**Назначение:** Фильтрация по партиции (период/патч)

**Для WoW:** Обычно соответствует сезонам

**Примеры:**
```graphql
# Текущая партиция
partition: 1

# Предыдущий сезон
partition: 2
```

**По умолчанию:** Последняя партиция

---

### 8. `serverRegion: String` и `serverSlug: String`
**Назначение:** Фильтрация по региону и/или серверу

**Примеры регионов:**
- `"EU"` - Европа
- `"US"` - США
- `"KR"` - Корея
- `"TW"` - Тайвань
- `"CN"` - Китай

**Примеры:**
```graphql
# Только EU
serverRegion: "EU"

# Конкретный сервер
serverRegion: "EU"
serverSlug: "tarren-mill"

# Все серверы US
serverRegion: "US"
```

---

### 9. `size: Int`
**Назначение:** Размер рейдовой группы

**Для WoW:** Обычно `10`, `20`, `25`, `30`

**Примеры:**
```graphql
# Рейд на 20 человек
size: 20
```

**Примечание:** Для современных WoW рейдов не актуален (Mythic всегда 20 чел)

---

### 10. `leaderboard: LeaderboardRank`
**Назначение:** Включать ли записи без backing logs

**Значения:**
- `Default` - Только с логами
- `Any` - Все записи

**Примеры:**
```graphql
# Включить записи без логов (например, из Blizzard API)
leaderboard: Any
```

---

### 11. `hardModeLevel: HardModeLevelRankFilter`
**Назначение:** Фильтрация по уровню hard mode

**Для WoW Mythic+:**
- `0` - Нет аффиксов (не используется)
- `1-5` - Уровень сложности
- `-1` - Любой уровень

**Примеры:**
```graphql
# Конкретный уровень hard mode
hardModeLevel: 3

# Любой hard mode
hardModeLevel: -1
```

**Примечание:** Для большинства encounter не используется

---

## Параметры только для characterRankings

### 12. `className: String`
**Назначение:** Фильтрация по классу

**Примеры:**
```graphql
className: "Priest"
className: "Warrior"
className: "DeathKnight"
```

**Формат:** CamelCase (первая буква заглавная, пробелы убраны)

---

### 13. `specName: String`
**Назначение:** Фильтрация по специализации

**Примеры:**
```graphql
specName: "Shadow"
specName: "Protection"
specName: "BeastMastery"
```

**Формат:** CamelCase

---

### 14. `includeCombatantInfo: Boolean`
**Назначение:** Включить детальную информацию о персонаже

**Что включает:**
- Gear (экипировка)
- Таланты
- Enchants/Gems
- Soulbind/Covenant (для Shadowlands)

**Примеры:**
```graphql
# Получить информацию об экипировке
includeCombatantInfo: true
```

**Предупреждение:** Увеличивает размер ответа и время обработки

---

### 15. `externalBuffs: ExternalBuffRankFilter`
**Назначение:** Фильтрация по внешним баффам

**Значения:**
- `Any` - Любые
- `WithExternalBuffs` - Только с внешними баффами
- `WithoutExternalBuffs` - Только без внешних баффов

**Примеры:**
```graphql
# Только без Power Infusion и прочих внешних баффов
externalBuffs: WithoutExternalBuffs
```

**Примечание:** Поддерживается не для всех зон

---

### 16. `covenantID: Int` (Shadowlands)
**Назначение:** Фильтрация по ковенанту

**Shadowlands Covenant IDs:**
- `1` - Kyrian
- `2` - Venthyr
- `3` - Night Fae
- `4` - Necrolord

**Примеры:**
```graphql
# Только Night Fae
covenantID: 3
```

**Примечание:** Актуально только для Shadowlands контента

---

### 17. `soulbindID: Int` (Shadowlands)
**Назначение:** Фильтрация по soulbind

**Примеры:**
```graphql
# Конкретный soulbind
soulbindID: 7
```

**Примечание:** Актуально только для Shadowlands контента

---

## Практические примеры использования

### Пример 1: Базовый запрос для Mythic+

```graphql
query {
  worldData {
    encounter(id: 62660) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        metric: playerscore
      )
    }
  }
}
```

**Результат:** Все Shadow Priest рейтинги по RIO score

---

### Пример 2: Mythic+ high keys (12+)

```graphql
query {
  worldData {
    encounter(id: 62660) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        metric: playerscore
        bracket: 12
      )
    }
  }
}
```

**Результат:** Только ключи 12+ уровня

---

### Пример 3: Mythic Raid с конкретным ilvl

```graphql
query {
  worldData {
    encounter(id: 2902) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        difficulty: 5
        metric: dps
        bracket: 638
      )
    }
  }
}
```

**Результат:** Только персонажи с ilvl 638+ на Mythic сложности

---

### Пример 4: Только живые персонажи (no deaths)

```graphql
query {
  worldData {
    encounter(id: 2902) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        difficulty: 5
        metric: dps
        filter: "death=0"
      )
    }
  }
}
```

**Результат:** Только парсы без смертей

---

### Пример 5: Конкретный регион и сервер

```graphql
query {
  worldData {
    encounter(id: 62660) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        metric: playerscore
        serverRegion: "EU"
        serverSlug: "tarren-mill"
      )
    }
  }
}
```

**Результат:** Только с сервера Tarren Mill (EU)

---

### Пример 6: Без внешних баффов

```graphql
query {
  worldData {
    encounter(id: 2902) {
      name
      characterRankings(
        className: "Mage"
        specName: "Fire"
        difficulty: 5
        metric: dps
        externalBuffs: WithoutExternalBuffs
      )
    }
  }
}
```

**Результат:** Fire Mage без Power Infusion и других внешних баффов

---

### Пример 7: С детальной информацией о gear

```graphql
query {
  worldData {
    encounter(id: 2902) {
      name
      characterRankings(
        className: "Priest"
        specName: "Shadow"
        difficulty: 5
        metric: dps
        page: 1
        includeCombatantInfo: true
      )
    }
  }
}
```

**Результат:** Топ рейтинги с полной информацией об экипировке

---

### Пример 8: Fight rankings (скорость килла)

```graphql
query {
  worldData {
    encounter(id: 2902) {
      name
      fightRankings(
        difficulty: 5
        metric: speed
        serverRegion: "EU"
      )
    }
  }
}
```

**Результат:** Самые быстрые киллы босса на EU Mythic

---

## Структура ответа

### characterRankings возвращает JSON:

```json
{
  "page": 1,
  "hasMorePages": true,
  "count": 100,
  "rankings": [
    {
      "name": "PlayerName",
      "class": "Priest",
      "spec": "Shadow",
      "amount": 2132587,        // DPS/HPS для raid
      "score": 515.47,          // RIO score для M+
      "bracketData": 22,        // M+ level или item level
      "hardModeLevel": 22,      // M+ level
      "medal": "bronze",        // M+ medal
      "duration": 32450,        // Длительность боя (raid)
      "server": {
        "id": 340,
        "name": "Tarren Mill",
        "region": "EU"
      },
      "report": {
        "code": "abc123",
        "fightID": 15,
        "startTime": 1234567890
      }
    }
  ]
}
```

### fightRankings возвращает JSON:

```json
{
  "page": 1,
  "hasMorePages": true,
  "count": 100,
  "rankings": [
    {
      "guild": {
        "name": "Guild Name",
        "server": {
          "name": "Tarren Mill",
          "region": "EU"
        }
      },
      "duration": 254321,       // Время убийства (мс)
      "execution": 95.5,        // Execution rating
      "bracket": 639,           // Item level
      "report": {
        "code": "abc123",
        "fightID": 10,
        "startTime": 1234567890
      }
    }
  ]
}
```

---

## Рекомендации по использованию

### 1. Оптимизация запросов

**Плохо:**
```python
# Множество запросов по одному
for bracket in range(12, 23):
    fetch_rankings(bracket=bracket)
```

**Хорошо:**
```python
# Один запрос с минимальным bracket, фильтруем руками
rankings = fetch_rankings(bracket=12)
low_keys = [r for r in rankings if r['bracketData'] <= 17]
high_keys = [r for r in rankings if r['bracketData'] > 17]
```

---

### 2. Комбинирование фильтров

```graphql
characterRankings(
  difficulty: 5                           # Mythic
  metric: dps                             # DPS метрика
  bracket: 638                            # ilvl 638+
  filter: "death=0 AND ilvl>=638"         # Без смертей
  externalBuffs: WithoutExternalBuffs     # Без внешних баффов
  serverRegion: "EU"                      # Только EU
  page: 1                                 # Первая страница
)
```

---

### 3. Использование filter для сложной логики

**Примеры фильтров:**
```
# Конкретный item level диапазон
"ilvl>=638 AND ilvl<=639"

# Без смертей, с определенным ilvl
"death=0 AND ilvl>=638"

# Конкретная ability использована N раз
"ability.id=12345.uses>=5"

# Время боя меньше X
"duration<300000"
```

---

## Ограничения и лимиты

### Rate Limiting
- ~300 requests/hour для OAuth приложений
- Используйте параллельные запросы с `asyncio.gather`
- Добавьте retry logic для 429 ошибок

### Пагинация
- По умолчанию 100 записей на страницу
- Используйте `hasMorePages` для проверки наличия следующей страницы

### Кеширование
- Данные меняются в реал-тайме
- Кешируйте результаты локально на 1-24 часа
- Для критичных данных используйте короткий TTL

---

## Интеграция в ваш проект

### Пример функции с множественными фильтрами

```python
async def fetch_advanced_rankings(
    client: httpx.AsyncClient,
    token: str,
    encounter_id: int,
    content_type: str = "mythic_plus",
    # Базовые параметры
    class_name: Optional[str] = None,
    spec_name: Optional[str] = None,
    # Фильтры
    difficulty: Optional[int] = None,
    bracket: Optional[int] = None,
    filter_string: Optional[str] = None,
    # Региональные фильтры
    server_region: Optional[str] = None,
    server_slug: Optional[str] = None,
    # Продвинутые
    external_buffs: Optional[str] = None,
    include_combatant_info: bool = False,
    page: int = 1
) -> Optional[Dict]:
    """
    Универсальная функция для получения рейтингов с множественными фильтрами
    """

    # Определяем метрику
    if content_type == "mythic_plus":
        metric = "playerscore"
    else:
        spec_role, _ = SPEC_ROLE_METRIC.get(spec_name, ("dps", "dps"))
        metric = "hps" if spec_role == "healer" else "dps"

    # Строим query
    query = """
    query(
      $encounterID: Int!,
      $className: String,
      $specName: String,
      $difficulty: Int,
      $bracket: Int,
      $filter: String,
      $serverRegion: String,
      $serverSlug: String,
      $externalBuffs: ExternalBuffRankFilter,
      $includeCombatantInfo: Boolean,
      $metric: CharacterRankingMetricType,
      $page: Int
    ) {
      worldData {
        encounter(id: $encounterID) {
          name
          characterRankings(
            className: $className
            specName: $specName
            difficulty: $difficulty
            bracket: $bracket
            filter: $filter
            serverRegion: $serverRegion
            serverSlug: $serverSlug
            externalBuffs: $externalBuffs
            includeCombatantInfo: $includeCombatantInfo
            metric: $metric
            page: $page
          )
        }
      }
    }
    """

    variables = {
        "encounterID": encounter_id,
        "className": class_name,
        "specName": spec_name,
        "metric": metric,
        "page": page
    }

    # Добавляем опциональные параметры
    if difficulty is not None:
        variables["difficulty"] = difficulty
    if bracket is not None:
        variables["bracket"] = bracket
    if filter_string:
        variables["filter"] = filter_string
    if server_region:
        variables["serverRegion"] = server_region
    if server_slug:
        variables["serverSlug"] = server_slug
    if external_buffs:
        variables["externalBuffs"] = external_buffs
    if include_combatant_info:
        variables["includeCombatantInfo"] = True

    # Выполняем запрос
    try:
        r = await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query, "variables": variables},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        if "errors" in data:
            logger.error(f"GraphQL error: {data['errors']}")
            return None

        return data.get("data", {}).get("worldData", {}).get("encounter", {}).get("characterRankings")

    except Exception as e:
        logger.error(f"Error fetching rankings: {e}")
        return None
```

### Примеры использования:

```python
# 1. High keys EU только
rankings = await fetch_advanced_rankings(
    client, token, 62660,
    content_type="mythic_plus",
    class_name="Priest",
    spec_name="Shadow",
    bracket=18,
    server_region="EU"
)

# 2. Mythic raid без смертей, высокий ilvl
rankings = await fetch_advanced_rankings(
    client, token, 2902,
    content_type="raid",
    class_name="Mage",
    spec_name="Fire",
    difficulty=5,
    bracket=638,
    filter_string="death=0",
    external_buffs="WithoutExternalBuffs"
)

# 3. Конкретный сервер с gear info
rankings = await fetch_advanced_rankings(
    client, token, 2902,
    content_type="raid",
    class_name="Priest",
    spec_name="Shadow",
    difficulty=5,
    server_region="EU",
    server_slug="tarren-mill",
    include_combatant_info=True
)
```

---

## Сводная таблица параметров

| Параметр | Тип | Где используется | Описание |
|----------|-----|------------------|----------|
| `bracket` | Int | characterRankings, fightRankings | Минимальный M+ level или item level |
| `difficulty` | Int | characterRankings, fightRankings | 3=Normal, 4=Heroic, 5=Mythic |
| `filter` | String | characterRankings, fightRankings | Продвинутый поисковой синтаксис |
| `page` | Int | characterRankings, fightRankings | Номер страницы (пагинация) |
| `partition` | Int | characterRankings, fightRankings | Сезон/партиция |
| `serverRegion` | String | characterRankings, fightRankings | Регион (EU, US, KR, etc) |
| `serverSlug` | String | characterRankings, fightRankings | Slug сервера |
| `size` | Int | characterRankings, fightRankings | Размер рейда |
| `leaderboard` | Enum | characterRankings, fightRankings | Default/Any |
| `hardModeLevel` | Enum | characterRankings, fightRankings | Уровень hard mode (-1 до 5) |
| `metric` | Enum | characterRankings | playerscore/dps/hps/etc |
| `metric` | Enum | fightRankings | speed/execution/feats |
| `includeCombatantInfo` | Boolean | characterRankings | Включить gear информацию |
| `className` | String | characterRankings | Фильтр по классу |
| `specName` | String | characterRankings | Фильтр по специализации |
| `externalBuffs` | Enum | characterRankings | Any/WithExternalBuffs/WithoutExternalBuffs |
| `covenantID` | Int | characterRankings | ID ковенанта (Shadowlands) |
| `soulbindID` | Int | characterRankings | ID soulbind (Shadowlands) |

---

## Заключение

WarcraftLogs API предоставляет мощную систему фильтрации для получения точных данных. Основные советы:

1. **Используйте комбинации фильтров** для получения нужных данных
2. **Кешируйте результаты** для снижения нагрузки на API
3. **filter** параметр - самый гибкий, изучите синтаксис на сайте
4. **bracket** работает как минимальный порог, используйте ручную фильтрацию для max значений
5. **externalBuffs** и **filter="death=0"** для получения "чистых" парсов

Для получения детальной информации о синтаксисе фильтров, используйте поиск на warcraftlogs.com и копируйте строку фильтра из URL.
