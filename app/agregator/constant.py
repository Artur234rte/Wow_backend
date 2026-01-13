import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
API_URL = "https://www.warcraftlogs.com/api/v2/client"
RIO_URL = url = "https://raider.io/api/v1/characters/profile"
WOW_CLASS_SPECS = {
    "DeathKnight": ["Blood", "Frost", "Unholy"],
    "DemonHunter": ["Havoc", "Vengeance"],
    "Druid": ["Balance", "Feral", "Guardian", "Restoration"],
    "Evoker": ["Devastation", "Preservation", "Augmentation"],
    "Hunter": ["BeastMastery", "Marksmanship", "Survival"],
    "Mage": ["Arcane", "Fire", "Frost"],
    "Monk": ["Brewmaster", "Mistweaver", "Windwalker"],
    "Paladin": ["Holy", "Protection", "Retribution"],
    "Priest": ["Discipline", "Holy", "Shadow"],
    "Rogue": ["Assassination", "Outlaw", "Subtlety"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"],
}
SPEC_ROLE_METRIC = {
    "Blood":        ("tank", "playerscore"),
    "Frost":        ("dps",  "playerscore"),
    "Unholy":       ("dps",  "playerscore"),
    "Vengeance":    ("tank", "playerscore"),
    "Havoc":        ("dps",  "playerscore"),
    "Guardian":     ("tank", "playerscore"),
    "Feral":        ("dps",  "playerscore"),
    "Balance":      ("dps",  "playerscore"),
    "Restoration":  ("healer", "playerscore"),
    "Preservation": ("healer", "playerscore"),
    "Devastation":  ("dps",    "playerscore"),
    "Augmentation": ("dps",    "playerscore"),
    "BeastMastery":("dps", "playerscore"),
    "Marksmanship": ("dps", "playerscore"),
    "Survival":     ("dps", "playerscore"),
    "Arcane":       ("dps", "playerscore"),
    "Fire":         ("dps", "playerscore"),
    "Frost":        ("dps", "playerscore"),
    "Brewmaster":   ("tank", "playerscore"),
    "Windwalker":   ("dps",  "playerscore"),
    "Mistweaver":   ("healer", "playerscore"),
    "Protection":   ("tank", "playerscore"),
    "Retribution":  ("dps",  "playerscore"),
    "Holy":         ("healer", "playerscore"),
    "Discipline":   ("healer", "playerscore"),
    "Holy":         ("healer", "playerscore"),
    "Shadow":       ("dps",  "playerscore"),
    "Assassination":("dps", "playerscore"),
    "Outlaw":       ("dps", "playerscore"),
    "Subtlety":     ("dps", "playerscore"),
    "Elemental":    ("dps", "playerscore"),
    "Enhancement":  ("dps", "playerscore"),
    "Restoration":  ("healer", "playerscore"),
    "Affliction":   ("dps", "playerscore"),
    "Demonology":   ("dps", "playerscore"),
    "Destruction":  ("dps", "playerscore"),
    "Protection":   ("tank", "playerscore"),
    "Arms":         ("dps",  "playerscore"),
    "Fury":         ("dps",  "playerscore"),
}

ENCOUNTERS = [
    62660,   # Ulgrax the Devourer
    12830,   # The Bloodbound Horror
    # 62287,   # Sikran
    # 62773,   # Rasha'nan
    # 62649,   # Broodtwister Ovi'nax
    # 112442,  # Nexus-Princess Ky'veza
    # 112441,  # The Silken Court
    # 62662    # Queen Ansurek
]