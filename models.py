import datetime
import enum
from sqlalchemy import (
    Column, BigInteger, String, Float, Integer, Boolean,
    DateTime, Date, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Rarity(str, enum.Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


RARITY_INCOME = {
    Rarity.COMMON: 1.0,
    Rarity.UNCOMMON: 1.5,
    Rarity.RARE: 2.5,
    Rarity.EPIC: 5.0,
    Rarity.LEGENDARY: 10.0,
}

RARITY_NAMES = {
    Rarity.COMMON: "⬜ Обычный",
    Rarity.UNCOMMON: "🟩 Необычный",
    Rarity.RARE: "🟦 Редкий",
    Rarity.EPIC: "🟪 Эпический",
    Rarity.LEGENDARY: "🟨 Легендарный",
}


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    balance = Column(Float, default=100.0)
    crystals = Column(Integer, default=0)
    prestige_level = Column(Integer, default=0)
    daily_transferred = Column(Float, default=0.0)
    last_transfer_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    DAILY_TRANSFER_LIMIT = 2000.0
    TRANSFER_TAX = 0.05

    @property
    def transfer_remaining(self) -> float:
        today = datetime.datetime.utcnow().date()
        if self.last_transfer_date != today:
            return self.DAILY_TRANSFER_LIMIT
        return max(0, self.DAILY_TRANSFER_LIMIT - self.daily_transferred)


class Slave(Base):
    __tablename__ = "slaves"

    id = Column(BigInteger, primary_key=True)
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    target_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    level = Column(Integer, default=1)
    rarity = Column(SQLEnum(Rarity), default=Rarity.COMMON)
    fatigue = Column(Float, default=0.0)
    working = Column(Boolean, default=False)
    work_start = Column(DateTime, nullable=True)
    bought_for = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    newcomer_market = Column(Boolean, default=False)
    newcomer_listed_at = Column(DateTime, nullable=True)
    last_bought_at = Column(DateTime, nullable=True)

    NEWCOMER_MAX_LEVEL = 10
    NEWCOMER_MAX_PRICE = 500.0
    NEWCOMER_BUYER_MAX_BALANCE = 5000.0
    NEWCOMER_BUYER_MAX_AGE_DAYS = 14
    NEWCOMER_TAX = 0.03
    NEWCOMER_COOLDOWN_HOURS = 24

    owner = relationship("User", foreign_keys=[owner_id])
    target = relationship("User", foreign_keys=[target_id])

    @property
    def slave_class(self) -> tuple[str, float]:
        classes = [
            (40, "👑 Легенда", 60.0),
            (30, "🔮 Маг", 35.0),
            (25, "🛡️ Мастер", 20.0),
            (20, "💰 Торговец", 12.0),
            (15, "🗡️ Кузнец", 7.0),
            (10, "⛏️ Шахтёр", 4.0),
            (5, "🔨 Рабочий", 2.0),
            (1, "👤 Раб", 1.0),
        ]
        for min_lvl, name, mult in classes:
            if self.level >= min_lvl:
                return name, mult
        return "👤 Раб", 1.0

    @property
    def income_per_hour(self) -> float:
        from services.economy import calc_income
        _, class_mult = self.slave_class
        return calc_income(self.level, class_mult, RARITY_INCOME[self.rarity], self.fatigue)

    @property
    def next_upgrade_cost(self) -> float:
        from services.economy import calc_upgrade_cost
        return calc_upgrade_cost(self.level)

    @property
    def market_price(self) -> float:
        from services.economy import calc_buy_price
        return calc_buy_price(self)