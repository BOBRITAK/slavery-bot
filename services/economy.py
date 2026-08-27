BASE_INCOME = 5.0
BASE_UPGRADE_COST = 50.0
INCOME_EXPONENT = 0.65
UPGRADE_EXPONENT = 1.8
BUY_MULTIPLIER = 2.0
TAX_RATE = 0.08

RARITY_BUY_BONUS = {
    "common": 1.0,
    "uncommon": 1.3,
    "rare": 1.7,
    "epic": 2.5,
    "legendary": 4.0,
}


def calc_income(level: int, class_mult: float, rarity_mult: float, fatigue: float = 0.0) -> float:
    level_factor = level ** INCOME_EXPONENT
    fatigue_penalty = max(0.2, 1.0 - fatigue / 150.0)
    return round(BASE_INCOME * class_mult * rarity_mult * level_factor * fatigue_penalty, 2)


def calc_upgrade_cost(level: int) -> float:
    if level >= 50:
        return float('inf')
    return round(BASE_UPGRADE_COST * (level ** UPGRADE_EXPONENT), 2)


def calc_buy_price(slave) -> float:
    upgrade = calc_upgrade_cost(slave.level)
    rarity_bonus = RARITY_BUY_BONUS.get(slave.rarity.value, 1.0)
    return round(upgrade * BUY_MULTIPLIER * rarity_bonus, 2)


def calc_tax(price: float, rate: float = TAX_RATE) -> float:
    return round(price * rate, 2)