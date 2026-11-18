import asyncio
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
BOT_TOKEN = "9010767706:AAEcLfjhybDJTP8WSxHQJLUL3elhCvsutwE" 
ADMIN_ID = 8979656703
BOT_USERNAME = "bagdauserbot"
# ==============================================

router = Router()

class BetState(StatesGroup):
    waiting_bet = State()

class BankState(StatesGroup):
    deposit = State()
    withdraw = State()

user_game = {}

GAME_NAMES = {
    "basket": "🏀 Баскетбол",
    "foot": "⚽ Футбол",
    "darts": "🎯 Дартс",
    "bowling": "🎳 Боулинг",
    "dice": "🎲 Кубик",
    "slots": "🎰 Слоты",
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
        [InlineKeyboardButton(text="1 000 ₽", callback_data="bet_1000"),
         InlineKeyboardButton(text="10 000 ₽", callback_data="bet_10000")],
        [InlineKeyboardButton(text="50 000 ₽", callback_data="bet_50000"),
         InlineKeyboardButton(text="100 000 ₽", callback_data="bet_100000")],
    ])

def bank_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Депозит", callback_data="bank_dep"),
         InlineKeyboardButton(text="💸 Снять", callback_data="bank_wd")],
        [InlineKeyboardButton(text="📊 Мой вклад", callback_data="bank_info")],
    ])

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
        f"👋 Добро пожаловать!\n\n"
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
        f"💰 Баланс: {u['balance']:,} ₽\n"
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
        f"👤 Профиль\n\n"
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
    lines = ["📜 Последние 10 игр:\n"]
    for game, bet, result, payout, ts in rows:
        t = time.strftime("%d.%m %H:%M", time.localtime(ts))
        sign = "✅" if payout > 0 else "❌"
        lines.append(f"{sign} {t} | {game} | ставка {bet:,} | выигрыш {payout:,}")
    await msg.answer("\n".join(lines))

# ---------- Ежедневный бонус ----------
@router.message(F.text == "🎁 Бонус")
async def daily(msg: Message):
    ok, info = await db.claim_daily(msg.from_user.id)
    if ok:
        bal = await db.get_balance(msg.from_user.id)
        await msg.answer(
            f"🎁 Ежедневный бонус получен!\n"
            f"+{info:,} ₽\n"
            f"💰 Баланс: {bal:,} ₽"
        )
    else:
        hours = info // 3600
        minutes = (info % 3600) // 60
        await msg.answer(f"⏳ Бонус уже получен.\nСледующий через {hours}ч {minutes}м.")

# ---------- Банк ----------
@router.message(F.text == "🏦 Банк")
async def bank_menu(msg: Message):
    u = await db.get_user(msg.from_user.id)
    await msg.answer(
        f"🏦 Банк\n\n"
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
        f"📊 Твой вклад: {u['bank']:,} ₽\n"
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
        "❓ Помощь\n\n"
        "🎮 Игры — выбери игру и ставку\n"
        "🎁 Бонус — раз в 24 часа\n"
        "🏦 Банк — депозит и снятие (+5%)\n"
        "👤 Профиль — статистика\n"
        "📜 История — последние 10 игр\n"
        "🔗 Рефералка — приглашай друзей\n\n"
        f"Мин. ставка: {db.MIN_BET:,} ₽"
    )

# ---------- Админ (Донат) ----------
@router.message(F.text == "👑 Админ-баланс")
async def admin_balance(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔ Только для админа.")
        return
    
    await db.set_balance(msg.from_user.id, 10_000_000_000)
    await msg.answer("👑 Установлено 10 000 000 000 ₽ (бесконечная валюта)")

# ---------- Игры ----------
@router.message(F.text == "🎮 Игры")
async def show_games(msg: Message):
    await msg.answer("Выбери игру:", reply_markup=games_kb())

@router.callback_query(F.data.startswith("game_"))
async def choose_game(call: CallbackQuery):
    game = call.data.split("_", 1)[1]
    user_game[call.from_user.id] = {"game": game, "bet": None}

    if game == "slots":
        await call.message.edit_text(
            f"🎰 Слоты\nЦена прокрута: {games.SLOT_COST} ₽\n"
            f"777 — бонус {games.SLOT_JACKPOT_BONUS} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Крутить", callback_data="slots_spin")]
            ])
        )
        return

    await call.message.edit_text(
        f"{GAME_NAMES[game]}\nВыбери ставку (мин {db.MIN_BET:,} ₽):",
        reply_markup=bet_kb(),
    )

@router.callback_query(F.data.startswith("bet_"))
async def set_bet(call: CallbackQuery):
    bet = int(call.data.split("_")[1])
    state = user_game.get(call.from_user.id)
    if not state:
        await call.answer("Сначала выбери игру", show_alert=True)
        return

    bal = await db.get_balance(call.from_user.id)
    if bal < bet:
        await call.answer(f"Недостаточно средств. Баланс: {bal:,} ₽", show_alert=True)
        return
    if bet < db.MIN_BET:
        await call.answer(f"Минимальная ставка {db.MIN_BET:,} ₽", show_alert=True)
        return

    state["bet"] = bet
    game = state["game"]

    if game == "basket":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попадание x2.4", callback_data="choice_hit"),
             InlineKeyboardButton(text="Мимо x1.6", callback_data="choice_miss")],
        ])
    elif game == "foot":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Гол x1.6", callback_data="choice_goal"),
             InlineKeyboardButton(text="Мимо x2.4", callback_data="choice_miss")],
        ])
    elif game == "darts":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Красное x1.94", callback_data="choice_red"),
             InlineKeyboardButton(text="Белое x2.9", callback_data="choice_white")],
            [InlineKeyboardButton(text="Центр x5.8", callback_data="choice_center"),
             InlineKeyboardButton(text="Мимо x5.8", callback_data="choice_miss")],
        ])
    elif game == "bowling":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 кегля x5.8", callback_data="choice_1"),
             InlineKeyboardButton(text="3 кегли x5.8", callback_data="choice_3")],
            [InlineKeyboardButton(text="4 кегли x5.8", callback_data="choice_4"),
             InlineKeyboardButton(text="Страйк x5.8", callback_data="choice_strike")],
            [InlineKeyboardButton(text="Мимо x5.8", callback_data="choice_miss")],
        ])
    elif game == "dice":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Чёт x1.94", callback_data="choice_even"),
             InlineKeyboardButton(text="Нечёт x1.94", callback_data="choice_odd")],
            [InlineKeyboardButton(text="Ровно 3 x1.94", callback_data="choice_3"),
             InlineKeyboardButton(text="=3 x5.8", callback_data="choice_equal3")],
            [InlineKeyboardButton(text="НЕ 3 x2.9", callback_data="choice_minus3"),
             InlineKeyboardButton(text="Ровно 6 x5.8", callback_data="choice_6")],
        ])
    else:
        await call.message.edit_text("Что-то пошло не так")
        return

    await call.message.edit_text(
        f"Ставка: {bet:,} ₽\nСделай выбор:",
        reply_markup=kb,
    )

@router.callback_query(F.data.startswith("choice_"))
async def handle_choice(call: CallbackQuery):
    state = user_game.get(call.from_user.id)
    if not state or not state.get("bet"):
        await call.answer("Сначала выбери игру и ставку", show_alert=True)
        return

    game = state["game"]
    bet = state["bet"]
    choice = call.data.split("_", 1)[1]
    uid = call.from_user.id

    bal = await db.change_balance(uid, -bet)

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
            f"✅ Победа!\n"
            f"Результат: {outcome}\n"
            f"Коэффициент: x{coeff}\n"
            f"Выигрыш: +{payout:,} ₽\n"
            f"Баланс: {bal:,} ₽"
        )
    else:
        await db.add_history(uid, game, bet, outcome, 0)
        text = (
            f"❌ Проигрыш\n"
            f"Результат: {outcome}\n"
            f"Потеряно: -{bet:,} ₽\n"
            f"Баланс: {bal:,} ₽"
        )

    state["bet"] = None
    await call.message.edit_text(text, reply_markup=games_kb())

# ---------- Слоты ----------
@router.callback_query(F.data == "slots_spin")
async def slots_spin(call: CallbackQuery):
    uid = call.from_user.id
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
        await db.add_history(uid, "slots", games.SLOT_COST, "777", games.SLOT_JACKPOT_BONUS)
        text = (
            f"🎉 JACKPOT 777!\n"
            f"Бонус: +{games.SLOT_JACKPOT_BONUS} ₽\n"
            f"Баланс: {bal:,} ₽"
        )
    else:
        bal = await db.get_balance(uid)
        await db.add_history(uid, "slots", games.SLOT_COST, f"крут {value}", 0)
        text = (
            f"🎰 Прокрут: {value}\n"
            f"Стоимость: -{games.SLOT_COST} ₽\n"
            f"Баланс: {bal:,} ₽"
        )

    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Крутить ещё", callback_data="slots_spin")]
    ]))

# ---------- Запуск ----------
async def main():
    await db.init_db()
    
    # ВЕРСИЯ ДЛЯ RENDER (БЕЗ ПРОКСИ)
    bot = Bot(token=BOT_TOKEN)
    
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
