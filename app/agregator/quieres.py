q_with_gear_and_talent = """
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: playerscore
        includeCombatantInfo: true,
      )
    }
  }
}
"""

QUERY_FOR_MYTHIC_PLUS_LOW_KEYS = """
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: dps
        leaderboard: LogsOnly
        bracket: 11
      )
    }
  }
}
"""
QUERY_FOR_POPULARITY_LOW_KEYS = """
query(
  $encounterID: Int!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        metric: dps
        bracket: 11
      )
    }
  }
}
"""

QUERY_FOR_POPULARITY_HIGH_KEYS = """
query(
  $encounterID: Int!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        metric: dps
      )
    }
  }
}
"""

QUERY_FOR_MYTHIC_PLUS_HIGH_KEYS = """
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: dps
        leaderboard: LogsOnly
      )
    }
  }
}
"""

QUERY_FOR_RAID_DPS ="""
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: dps
        leaderboard: LogsOnly
        difficulty: 5
      )
    }
  }
}
"""

QUERY_FOR_RAID_HPS ="""
query(
  $encounterID: Int!,
  $className: String!,
  $specName: String!,
) {
  worldData {
    encounter(id: $encounterID) {
      name
      characterRankings(
        className: $className
        specName: $specName
        metric: hps
        leaderboard: LogsOnly
        difficulty: 5
      )
    }
  }
}
"""


q_balance = '''
query {
  rateLimitData {
    limitPerHour
    pointsSpentThisHour
    pointsResetIn
  }
}
'''