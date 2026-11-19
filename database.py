import aiosqlite
import time

DB_PATH = "bot.db"
START_BALANCE = 150_000
MIN_BET = 10_000
DAILY_BONUS = 5_000
DAILY_COOLDOWN = 24 * 60 * 60
BANK_RATE = 0.05
BANK_MIN = 10_000_000
REF_BONUS = 10_000
ADMIN_ID = 8979656703


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                bank INTEGER NOT NULL DEFAULT 0,
                last_daily INTEGER NOT NULL DEFAULT 0,
                referrer_id INTEGER,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                bet INTEGER NOT NULL,
                result TEXT NOT NULL,
                payout INTEGER NOT NULL,
                ts INTEGER NOT NULL
            )
        """)
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id, balance, bank, last_daily, referrer_id, username "
            "FROM users WHERE user_id=?", (user_id,)
        )
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, balance) VALUES (?, ?)",
                (user_id, START_BALANCE),
            )
            await db.commit()
            return {
                "user_id": user_id, "balance": START_BALANCE,
                "bank": 0, "last_daily": 0,
                "referrer_id": None, "username": None,
            }
        return {
            "user_id": row[0], "balance": row[1], "bank": row[2],
            "last_daily": row[3], "referrer_id": row[4], "username": row[5],
        }


async def get_balance(user_id: int) -> int:
    u = await get_user(user_id)
    return u["balance"]


async def set_balance(user_id: int, value: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET balance=excluded.balance",
            (user_id, value),
        )
        await db.commit()


async def change_balance(user_id: int, delta: int) -> int:
    if user_id == ADMIN_ID and delta < 0:
        u = await get_user(user_id)
        return u["balance"]

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, ?)",
            (user_id, START_BALANCE),
        )
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?",
            (delta, user_id),
        )
        await db.commit()
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0]


async def add_history(user_id: int, game: str, bet: int, result: str, payout: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO history (user_id, game, bet, result, payout, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, game, bet, result, payout, int(time.time())),
        )
        await db.commit()


async def get_history(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT game, bet, result, payout, ts FROM history "
            "WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return await cur.fetchall()


async def claim_daily(user_id: int):
    u = await get_user(user_id)
    now = int(time.time())
    if now - u["last_daily"] < DAILY_COOLDOWN:
        wait = DAILY_COOLDOWN - (now - u["last_daily"])
        return False, wait
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id=?",
            (DAILY_BONUS, now, user_id),
        )
        await db.commit()
    return True, DAILY_BONUS


async def bank_deposit(user_id: int, amount: int):
    u = await get_user(user_id)
    if amount < BANK_MIN:
        return False, f"Минимум {BANK_MIN:,} ₽"
    if u["balance"] < amount:
        return False, "Недостаточно средств"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance - ?, bank = bank + ? WHERE user_id=?",
            (amount, amount, user_id),
        )
        await db.commit()
    return True, amount


async def bank_withdraw(user_id: int, amount: int):
    u = await get_user(user_id)
    if amount > u["bank"]:
        return False, "В банке недостаточно средств"
    bonus = int(amount * BANK_RATE)
    total = amount + bonus
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET bank = bank - ?, balance = balance + ? WHERE user_id=?",
            (amount, total, user_id),
        )
        await db.commit()
    return True, (amount, bonus)


async def set_referrer(user_id: int, ref_id: int):
    if user_id == ref_id:
        return False
    u = await get_user(user_id)
    if u["referrer_id"] is not None:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referrer_id=? WHERE user_id=?",
            (ref_id, user_id),
        )
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id=?",
            (REF_BONUS, ref_id),
        )
        await db.commit()
    return True


async def count_referrals(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id=?", (user_id,)
        )
        row = await cur.fetchone()
        return row[0]
