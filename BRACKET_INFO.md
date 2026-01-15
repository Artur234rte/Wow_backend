# Поле bracket в WarcraftLogs API

## Описание

**`bracket`** - это параметр для фильтрации рейтингов по определенному "уровню" контента.

Для World of Warcraft brackets означают:
- **Mythic+**: Уровень ключа (keystone level) - например, 19, 20, 21, 22
- **Raids**: Item level диапазон

## В ответе API: поле `bracketData`

В JSON ответе от API это поле называется **`bracketData`** (не `bracket`!)

### Пример данных:
```json
{
  "name": "Librapriest",
  "class": "Priest",
  "spec": "Shadow",
  "hardModeLevel": 22,
  "bracketData": 22,
  "score": 515.4663125
}
```

### Возможные значения для Mythic+:

Из теста для босса Ulgrax the Devourer (encounter 62660), для Shadow Priest:

| bracketData | Значение | Количество записей |
|-------------|----------|-------------------|
| 19 | Mythic+19 | 75 записей |
| 20 | Mythic+20 | 20 записей |
| 21 | Mythic+21 | 4 записи |
| 22 | Mythic+22 | 1 запись |

**Важно:** `bracketData` всегда равен `hardModeLevel` для Mythic+ контента.

## В запросе GraphQL: параметр `bracket`

### Тип данных
- **Int** (целое число, опциональный параметр)

### Описание
> "A specific bracket (e.g., item level range) to use instead of overall rankings. For WoW, brackets are item levels or keystones. For FF, brackets are patches."

### Использование в запросе

```graphql
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
  $bracket: Int
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: playerscore
        bracket: $bracket
      )
    }
  }
}
```

### Примеры использования

#### 1. Без фильтра (все уровни)
```python
variables = {
    "encounterID": 62660,
    "className": "Priest",
    "specName": "Shadow"
}
# Результат: 100 записей (M+19, M+20, M+21, M+22)
```

#### 2. Фильтр по M+20
```python
variables = {
    "encounterID": 62660,
    "className": "Priest",
    "specName": "Shadow",
    "bracket": 20
}
# Результат: записи с уровнем ключа >= 20
# ВНИМАНИЕ: Фильтр работает как "от этого уровня и выше"!
```

#### 3. Фильтр по M+21
```python
variables = {
    "encounterID": 62660,
    "className": "Priest",
    "specName": "Shadow",
    "bracket": 21
}
# Результат: записи с уровнем ключа >= 21
```

## Особенности работы фильтра

⚠️ **ВАЖНО:** Параметр `bracket` работает как **минимальный порог**, а не как точное значение!

Наблюдения из тестов:
- `bracket: 20` → возвращает записи с `bracketData: 21` и выше
- `bracket: 21` → возвращает записи с `bracketData: 22` и выше
- `bracket: 22` → возвращает 0 записей (нет ключей выше M+22)

Это похоже на фильтрацию "показать только записи выше определенного уровня сложности".

## Связанные параметры

### hardModeLevel
- **Тип**: HardModeLevelRankFilter (ENUM)
- **Описание**: "Filters ranks to a specific hard mode (0-5) or any hard mode level (-1)"
- Для большинства encounter это не применимо, но для Mythic+ это аналог уровня ключа

### Другие параметры characterRankings:
- `difficulty` - сложность контента (Normal, Heroic, Mythic)
- `partition` - раздел/патч
- `serverRegion` - регион сервера
- `page` - страница результатов (пагинация)
- `leaderboard` - включать ли записи без логов
- `includeCombatantInfo` - включать ли детальную информацию о персонаже (gear, таланты)

## Примеры кода

### Python с использованием httpx
```python
import httpx

query = """
query($encounterID: Int!, $className: String!, $specName: String!, $bracket: Int) {
  worldData {
    encounter(id: $encounterID) {
      characterRankings(
        className: $className
        specName: $specName
        metric: playerscore
        bracket: $bracket
      )
    }
  }
}
"""

variables = {
    "encounterID": 62660,
    "className": "Priest",
    "specName": "Shadow",
    "bracket": 21  # Фильтр по M+21 и выше
}

async with httpx.AsyncClient() as client:
    r = await client.post(
        "https://www.warcraftlogs.com/api/v2/client",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "variables": variables}
    )
    data = r.json()

    # Получаем rankings
    rankings = data["data"]["worldData"]["encounter"]["characterRankings"]["rankings"]

    # Каждая запись имеет bracketData
    for rank in rankings:
        print(f"{rank['name']} - M+{rank['bracketData']} - Score: {rank['score']}")
```

## Итого

- **В ответе**: используйте `bracketData` (число)
- **В запросе**: используйте `bracket` (опциональный Int параметр)
- **Значения**: для Mythic+ это уровень ключа (19, 20, 21, 22, ...)
- **Фильтр**: работает как минимальный порог (>= указанного значения)
- **Чем выше bracket**, тем меньше записей (более сложный контент)

## Ссылки

- WarcraftLogs API: https://www.warcraftlogs.com/api/docs
- GraphQL Playground: https://www.warcraftlogs.com/api/graphiql
