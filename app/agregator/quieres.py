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

q_simple = """
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