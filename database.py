import asyncio
import os
import time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
import games

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9010767706:AAEcLfjhybDJTP8WSxHQJLUL3elhCvsutwE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8979656703"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "bagdauserbot")
# ==============================================

router = Router()

class BetState(StatesGroup):
    waiting_bet = State()

class BankState(StatesGroup):
    deposit = State()
    withdraw = State()

user_game = {}

# ---------- ЦВЕТОВЫЕ ТЕМЫ ----------
THEME = {
    "main":    "🟣",
    "games":   "🔵",
    "bet":     "🟢",
    "win":     "🟡",
    "lose":    "🔴",
    "bank":    "🟠",
    "bonus":   "🟤",
    "profile": "⚪",
    "admin":   "👑",
}

GAME_NAMES = {
    "basket": "🏀 Баскетбол",
    "foot": "⚽ Футбол",
    "darts": "🎯 Дартс",
    "bowling": "🎳 Боулинг",
    "dice": "🎲 Кубик",
    "slots": "🎰 Слоты",
}

GAME_HEADERS = {
    "basket":  "🏀 Баскетбол — попадание x2.4 / мимо x1.6",
    "foot":    "⚽ Футбол — гол x1.6 / мимо x2.4",
    "darts":   "🎯 Дартс — красное x1.94 / белое x2.9 / центр x5.8",
    "bowling": "🎳 Боулинг — 1/3/4 кегли x5.8 / страйк x5.8",
    "dice":    "🎲 Кубик — чёт/нечёт x1.94 / ровно 3 x1.94 / =3 x5.8 / НЕ3 x2.9 / 6 x5.8",
    "slots":   "🎰 Слоты — 777 = джекпот",
}

# Диапазоны риска для «своей суммы»
RISK_RANGES = {
    "light":  (10_000,      100_000),
    "medium": (100_000,   1_000_000),
    "red":    (1_000_000, 10_000_000),
}

# ---------- Клавиатуры ----------
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎮 Игры")],
            [KeyboardButton(text="🎁 Бонус"), KeyboardButton(text="🏦 Банк")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📜 История")],
            [KeyboardButton(text="🔗 Рефералка"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="👑 Админ-баланс")],
        ],
        resize_keyboard=True,
    )

def games_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=GAME_NAMES["basket"], callback_data="game_basket")],
        [InlineKeyboardButton(text=GAME_NAMES["foot"], callback_data="game_foot")],
        [InlineKeyboardButton(text=GAME_NAMES["darts"], callback_data="game_darts")],
        [InlineKeyboardButton(text=GAME_NAMES["bowling"], callback_data="game_bowling")],
        [InlineKeyboardButton(text=GAME_NAMES["dice"], callback_data="game_dice")],
        [InlineKeyboardButton(text=GAME_NAMES["slots"], callback_data="game_slots")],
    ])

def bet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 000 ₽",     callback_data="bet_10000"),
         InlineKeyboardButton(text="15 000 000 ₽", callback_data="bet_15000000")],
        [InlineKeyboardButton(text="25 000 000 ₽", callback_data="bet_25000000"),
         InlineKeyboardButton(text="50 000 000 ₽", callback_data="bet_50000000")],
        [InlineKeyboardButton(text="🟢 Лайт (10к–100к)",    callback_data="risk_light"),
         InlineKeyboardButton(text="🟡 Медиум (100к–1млн)", callback_data="risk_medium")],
        [InlineKeyboardButton(text="🔴 Ред (1млн–10млн)",   callback_data="risk_red")],
        [InlineKeyboardButton(text="✏️ Своя сумма", callback_data="bet_custom")],
    ])

def bank_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Депозит", callback_data="bank_dep"),
         InlineKeyboardButton(text="💸 Снять", callback_data="bank_wd")],
        [InlineKeyboardButton(text="📊 Мой вклад", callback_data="bank_info")],
    ])

def get_game_choice_kb(game: str):
    if game == "basket":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попадание x2.4", callback_data="choice_hit"),
             InlineKeyboardButton(text="Мимо x1.6", callback_data="choice_miss")],
        ])
    elif game == "foot":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Гол x1.6", callback_data="choice_goal"),
             InlineKeyboardButton(text="Мимо x2.4", callback_data="choice_miss")],
        ])
    elif game == "darts":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Красное x1.94", callback_data="choice_red"),
             InlineKeyboardButton(text="Белое x2.9", callback_data="choice_white")],
            [InlineKeyboardButton(text="Центр x5.8", callback_data="choice_center"),
             InlineKeyboardButton(text="Мимо x5.8", callback_data="choice_miss")],
        ])
    elif game == "bowling":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 кегля x5.8", callback_data="choice_1"),
             InlineKeyboardButton(text="3 кегли x5.8", callback_data="choice_3")],
            [InlineKeyboardButton(text="4 кегли x5.8", callback_data="choice_4"),
             InlineKeyboardButton(text="Страйк x5.8", callback_data="choice_strike")],
            [InlineKeyboardButton(text="Мимо x5.8", callback_data="choice_miss")],
        ])
    elif game == "dice":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Чёт x1.94", callback_data="choice_even"),
             InlineKeyboardButton(text="Нечёт x1.94", callback_data="choice_odd")],
            [InlineKeyboardButton(text="Ровно 3 x1.94", callback_data="choice_3"),
             InlineKeyboardButton(text="=3 x5.8", callback_data="choice_equal3")],
            [InlineKeyboardButton(text="НЕ 3 x2.9", callback_data="choice_minus3"),
             InlineKeyboardButton(text="Ровно 6 x5.8", callback_data="choice_6")],
        ])
    return None

# ---------- /start ----------
@router.message(CommandStart())
async def cmd_start(msg: Message):
    await db.get_user(msg.from_user.id)

    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].replace("ref_", ""))
            ok = await db.set_referrer(msg.from_user.id, ref_id)
            if ok:
                await msg.answer("✅ Вы пришли по реферальной ссылке! Бонус начислен пригласившему.")
        except ValueError:
            pass

    bal = await db.get_balance(msg.from_user.id)
    await msg.answer(
        f"{THEME['main']} Добро пожаловать!\n\n"
        f"💰 Баланс: {bal:,} ₽\n"
        f"🎯 Мин. ставка: {db.MIN_BET:,} ₽\n\n"
        f"Выбери действие 👇",
        reply_markup=main_kb(),
    )

# ---------- Баланс ----------
@router.message(F.text == "💰 Баланс")
async def show_balance(msg: Message):
    u = await db.get_user(msg.from_user.id)
    await msg.answer(
        f"{THEME['profile']} Баланс: {u['balance']:,} ₽\n"
        f"🏦 В банке: {u['bank']:,} ₽"
    )

# ---------- Профиль ----------
@router.message(F.text == "👤 Профиль")
async def profile(msg: Message):
    u = await db.get_user(msg.from_user.id)
    refs = await db.count_referrals(msg.from_user.id)
    hist = await db.get_history(msg.from_user.id, limit=100)
    wins = sum(1 for h in hist if h[3] > 0)
    total = len(hist)
    await msg.answer(
        f"{THEME['profile']} Профиль\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"💰 Баланс: {u['balance']:,} ₽\n"
        f"🏦 Банк: {u['bank']:,} ₽\n"
        f"🎮 Игр сыграно: {total}\n"
        f"🏆 Побед: {wins}\n"
        f"👥 Рефералов: {refs}",
        parse_mode="HTML",
    )

# ---------- История ----------
@router.message(F.text == "📜 История")
async def history(msg: Message):
    rows = await db.get_history(msg.from_user.id, limit=10)
    if not rows:
        await msg.answer("📜 История пуста — сыграй первую игру!")
        return
    lines = [f"{THEME['games']} Последние 10 игр:\n"]
    for game, bet, result, payout, ts in rows:
        t = time.strftime("%d.%m %H:%M", time.localtime(ts))
        sign = "✅" if payout > 0 else "❌"
        lines.append(f"{sign} {t} | {game} | ставка {bet:,} | выигрыш {payout:,}")
    await msg.answer("\n".join(lines))

# ---------- Ежедневный бонус ----------
@router.message(F.text == "🎁 Бонус")
async def daily(msg: Message):
    ok, info = await db.claim_daily(msg.from_user.id)
    if not ok:
        hours = info // 3600
        minutes = (info % 3600) // 60
        await msg.answer(f"{THEME['bonus']} Бонус уже получен.\nСледующий через {hours}ч {minutes}м.")
        return

    # db.claim_daily начислил DAILY_BONUS (5 000). Считаем активность и корректируем.
    hist = await db.get_history(msg.from_user.id, limit=50)
    today = int(time.time()) // 86400
    games_today = sum(1 for h in hist if h[4] // 86400 == today)

    base = db.DAILY_BONUS
    extra = min(games_today * 1_000, 10_000)
    bonus = base + extra
    if bonus != info:
        await db.change_balance(msg.from_user.id, bonus - info)

    bal = await db.get_balance(msg.from_user.id)
    await msg.answer(
        f"{THEME['bonus']} Бонус получен!\n"
        f"База: {base:,} ₽\n"
        f"Активность: +{extra:,} ₽ ({games_today} игр сегодня)\n"
        f"Итого: +{bonus:,} ₽\n"
        f"💰 Баланс: {bal:,} ₽"
    )

# ---------- Банк ----------
@router.message(F.text == "🏦 Банк")
async def bank_menu(msg: Message):
    u = await db.get_user(msg.from_user.id)
    await msg.answer(
        f"{THEME['bank']} Банк\n\n"
        f"Вклад: {u['bank']:,} ₽\n"
        f"Минимум: {db.BANK_MIN:,} ₽\n"
        f"Процент при снятии: +{int(db.BANK_RATE*100)}%\n\n"
        f"Выбери действие:",
        reply_markup=bank_kb(),
    )

@router.callback_query(F.data == "bank_info")
async def bank_info(call: CallbackQuery):
    u = await db.get_user(call.from_user.id)
    await call.message.edit_text(
        f"{THEME['bank']} Твой вклад: {u['bank']:,} ₽\n"
        f"Баланс: {u['balance']:,} ₽"
    )

@router.callback_query(F.data == "bank_dep")
async def bank_dep(call: CallbackQuery, state: FSMContext):
    await state.set_state(BankState.deposit)
    await call.message.edit_text(
        f"💰 Введи сумму для депозита (мин {db.BANK_MIN:,}):"
    )

@router.callback_query(F.data == "bank_wd")
async def bank_wd(call: CallbackQuery, state: FSMContext):
    await state.set_state(BankState.withdraw)
    await call.message.edit_text("💸 Введи сумму для снятия:")

@router.message(BankState.deposit)
async def bank_dep_amount(msg: Message, state: FSMContext):
    try:
        amount = int(msg.text.replace(" ", "").replace(",", ""))
    except ValueError:
        await msg.answer("Введи число")
        return
    ok, info = await db.bank_deposit(msg.from_user.id, amount)
    await state.clear()
    if ok:
        await msg.answer(f"✅ Депозит успешен: {amount:,} ₽")
    else:
        await msg.answer(f"❌ {info}")

@router.message(BankState.withdraw)
async def bank_wd_amount(msg: Message, state: FSMContext):
    try:
        amount = int(msg.text.replace(" ", "").replace(",", ""))
    except ValueError:
        await msg.answer("Введи число")
        return
    ok, info = await db.bank_withdraw(msg.from_user.id, amount)
    await state.clear()
    if ok:
        amount, bonus = info
        await msg.answer(f"✅ Снято: {amount:,} ₽\nБонус: +{bonus:,} ₽")
    else:
        await msg.answer(f"❌ {info}")

# ---------- Рефералка ----------
@router.message(F.text == "🔗 Рефералка")
async def ref_link(msg: Message):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{msg.from_user.id}"
    refs = await db.count_referrals(msg.from_user.id)
    await msg.answer(
        f"🔗 Твоя реферальная ссылка:\n"
        f"{link}\n\n"
        f"👥 Приглашено: {refs}\n"
        f"💸 За каждого друга: +{db.REF_BONUS:,} ₽"
    )

# ---------- Помощь ----------
@router.message(F.text == "❓ Помощь")
async def help_msg(msg: Message):
    await msg.answer(
        f"{THEME['main']} Помощь\n\n"
        "🎮 Игры — выбери игру и ставку\n"
        "🎁 Бонус — раз в 24 часа (5к–15к в зависимости от активности)\n"
        "🏦 Банк — депозит и снятие (+5%)\n"
        "👤 Профиль — статистика\n"
        "📜 История — последние 10 игр\n"
        "🔗 Рефералка — приглашай друзей\n\n"
        f"Мин. ставка: {db.MIN_BET:,} ₽\n"
        f"Режимы: 🟢 Лайт / 🟡 Медиум / 🔴 Ред"
    )

# ---------- Админ ----------
@router.message(F.text == "👑 Админ-баланс")
async def admin_balance(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔ Только для админа.")
        return

    await db.set_balance(msg.from_user.id, 10_000_000_000)
    await msg.answer(f"{THEME['admin']} Установлено 10 000 000 000 ₽ (бесконечная валюта)")

# ---------- Игры ----------
@router.message(F.text == "🎮 Игры")
async def show_games(msg: Message):
    await msg.answer(f"{THEME['games']} Выбери игру:", reply_markup=games_kb())

@router.callback_query(F.data.startswith("game_"))
async def choose_game(call: CallbackQuery):
    game = call.data.split("_", 1)[1]
    user_game[call.from_user.id] = {"game": game, "bet": None}

    if game == "slots":
        await call.message.edit_text(
            f"🎰 Слоты\nЦена прокрута: {games.SLOT_COST:,} ₽\n"
            f"777 — бонус {games.SLOT_JACKPOT_BONUS:,} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Крутить", callback_data="slots_spin")]
            ])
        )
        return

    await call.message.edit_text(
        f"{THEME['games']} {GAME_HEADERS[game]}\n\n"
        f"Выбери ставку (мин {db.MIN_BET:,} ₽):",
        reply_markup=bet_kb(),
    )

# ---------- Выбор ставки: фиксированная ----------
@router.callback_query(F.data.startswith("bet_") & ~F.data.in_({"bet_custom"}))
async def set_bet(call: CallbackQuery):
    # отсекаем risk_* (они обрабатываются отдельно)
    if call.data.startswith("bet_custom"):
        return

    bet = int(call.data.split("_")[1])
    st = user_game.get(call.from_user.id)
    if not st:
        await call.answer("Сначала выбери игру", show_alert=True)
        return

    if bet < db.MIN_BET:
        await call.answer(f"Минимальная ставка {db.MIN_BET:,} ₽", show_alert=True)
        return

    if call.from_user.id != ADMIN_ID:
        bal = await db.get_balance(call.from_user.id)
        if bal < bet:
            await call.answer(f"Недостаточно средств. Баланс: {bal:,} ₽", show_alert=True)
            return

    st["bet"] = bet
    st.pop("risk", None)
    game = st["game"]

    kb = get_game_choice_kb(game)
    if kb is None:
        await call.message.edit_text("Что-то пошло не так")
        return

    await call.message.edit_text(
        f"{THEME['bet']} Ставка: <b>{bet:,} ₽</b>\nСделай выбор:",
        parse_mode="HTML",
        reply_markup=kb,
    )

# ---------- Выбор ставки: режим риска ----------
@router.callback_query(F.data.startswith("risk_"))
async def choose_risk(call: CallbackQuery, state: FSMContext):
    risk = call.data.split("_", 1)[1]
    lo, hi = RISK_RANGES[risk]
    st = user_game.get(call.from_user.id)
    if not st:
        await call.answer("Сначала выбери игру", show_alert=True)
        return
    st["risk"] = risk
    await state.set_state(BetState.waiting_bet)
    await call.message.edit_text(
        f"{THEME['bet']} Режим: <b>{risk.upper()}</b>\n"
        f"Введи сумму от {lo:,} до {hi:,} ₽:",
        parse_mode="HTML",
    )

# ---------- Выбор ставки: своя сумма ----------
@router.callback_query(F.data == "bet_custom")
async def bet_custom(call: CallbackQuery, state: FSMContext):
    st = user_game.get(call.from_user.id)
    if not st:
        await call.answer("Сначала выбери игру", show_alert=True)
        return
    st.pop("risk", None)
    await state.set_state(BetState.waiting_bet)
    await call.message.edit_text(
        f"{THEME['bet']} Введи сумму ставки числом (мин {db.MIN_BET:,} ₽):"
    )

# ---------- Ввод произвольной суммы ----------
@router.message(BetState.waiting_bet)
async def bet_custom_amount(msg: Message, state: FSMContext):
    try:
        bet = int(msg.text.replace(" ", "").replace(",", ""))
    except ValueError:
        await msg.answer("❌ Введи целое число, например: 500000")
        return

    st = user_game.get(msg.from_user.id)
    if not st:
        await state.clear()
        await msg.answer("Сначала выбери игру через 🎮 Игры")
        return

    risk = st.get("risk")
    if risk:
        lo, hi = RISK_RANGES[risk]
        if not (lo <= bet <= hi):
            await msg.answer(
                f"❌ Для режима {risk.upper()} сумма должна быть "
                f"от {lo:,} до {hi:,} ₽"
            )
            return

    if bet < db.MIN_BET:
        await msg.answer(f"❌ Минимальная ставка {db.MIN_BET:,} ₽")
        return

    if msg.from_user.id != ADMIN_ID:
        bal = await db.get_balance(msg.from_user.id)
        if bet > bal:
            await msg.answer(f"❌ Недостаточно средств. Баланс: {bal:,} ₽")
            return

    st["bet"] = bet
    game = st["game"]
    await state.clear()

    kb = get_game_choice_kb(game)
    if kb is None:
        await msg.answer("Что-то пошло не так")
        return

    await msg.answer(
        f"{THEME['bet']} Ставка: <b>{bet:,} ₽</b>\nСделай выбор:",
        parse_mode="HTML",
        reply_markup=kb,
    )

# ---------- Обработка выбора исхода ----------
@router.callback_query(F.data.startswith("choice_"))
async def handle_choice(call: CallbackQuery):
    st = user_game.get(call.from_user.id)
    if not st or not st.get("bet"):
        await call.answer("Сначала выбери игру и ставку", show_alert=True)
        return

    game = st["game"]
    bet = st["bet"]
    choice = call.data.split("_", 1)[1]
    uid = call.from_user.id

    # Админ не платит — списание только для обычных
    if uid != ADMIN_ID:
        await db.change_balance(uid, -bet)
    bal = await db.get_balance(uid)

    if game == "basket":
        win, coeff, outcome = games.play_basket(choice)
    elif game == "foot":
        win, coeff, outcome = games.play_foot(choice)
    elif game == "darts":
        win, coeff, outcome = games.play_darts(choice)
    elif game == "bowling":
        win, coeff, outcome = games.play_bowling(choice)
    elif game == "dice":
        win, coeff, value = games.play_dice(choice)
        outcome = f"выпало {value}"
    else:
        await call.message.edit_text("Ошибка игры")
        return

    if win:
        payout = int(bet * coeff)
        bal = await db.change_balance(uid, payout)
        await db.add_history(uid, game, bet, outcome, payout)
        text = (
            f"{THEME['win']} <b>ПОБЕДА</b>\n"
            f"Результат: {outcome}\n"
            f"Коэффициент: x{coeff}\n"
            f"Выигрыш: <b>+{payout:,} ₽</b>\n"
            f"Баланс: {bal:,} ₽"
        )
    else:
        await db.add_history(uid, game, bet, outcome, 0)
        text = (
            f"{THEME['lose']} <b>ПРОИГРЫШ</b>\n"
            f"Результат: {outcome}\n"
            f"Потеряно: -{bet:,} ₽\n"
            f"Баланс: {bal:,} ₽"
        )

    st["bet"] = None
    st.pop("risk", None)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=games_kb())

# ---------- Слоты ----------
@router.callback_query(F.data == "slots_spin")
async def slots_spin(call: CallbackQuery):
    uid = call.from_user.id

    if uid != ADMIN_ID:
        bal = await db.get_balance(uid)
        if bal < games.SLOT_COST:
            await call.answer("Недостаточно средств", show_alert=True)
            return
        await db.change_balance(uid, -games.SLOT_COST)

    msg = await call.message.answer_dice(emoji="🎰")
    await asyncio.sleep(2)

    value = msg.dice.value
    if value == 64:
        bal = await db.change_balance(uid, games.SLOT_JACKPOT_BONUS)
        await db.add_history(uid, "slots", games.SLOT_CO
