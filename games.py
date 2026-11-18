import random

BASKET_HIT = 2.4
BASKET_MISS = 1.6

FOOT_GOAL = 1.6
FOOT_MISS = 2.4

DARTS = {
    "red": 1.94,
    "white": 2.9,
    "center": 5.8,
    "miss": 5.8,
}

BOWLING = {
    "1": 5.8,
    "3": 5.8,
    "4": 5.8,
    "strike": 5.8,
    "miss": 5.8,
}

DICE = {
    "even": 1.94,
    "odd": 1.94,
    "3": 1.94,
    "equal3": 5.8,
    "minus3": 2.9,
    "6": 5.8,
}

SLOT_COST = 10
SLOT_JACKPOT_BONUS = 2000

def play_basket(choice: str):
    outcome = random.choice(["hit", "miss"])
    coeff = BASKET_HIT if outcome == "hit" else BASKET_MISS
    win = choice == outcome
    return win, coeff, outcome

def play_foot(choice: str):
    outcome = random.choice(["goal", "miss"])
    coeff = FOOT_GOAL if outcome == "goal" else FOOT_MISS
    win = choice == outcome
    return win, coeff, outcome

def play_darts(choice: str):
    outcome = random.choice(["red", "white", "center", "miss"])
    coeff = DARTS[outcome]
    win = choice == outcome
    return win, coeff, outcome

def play_bowling(choice: str):
    outcome = random.choice(["1", "3", "4", "strike", "miss"])
    coeff = BOWLING[outcome]
    win = choice == outcome
    return win, coeff, outcome

def play_dice(choice: str):
    value = random.randint(1, 6)
    if choice == "even":
        win = value % 2 == 0
        coeff = DICE["even"]
    elif choice == "odd":
        win = value % 2 == 1
        coeff = DICE["odd"]
    elif choice in ("3", "equal3"):
        win = value == 3
        coeff = DICE["3"] if choice == "3" else DICE["equal3"]
    elif choice == "minus3":
        win = value != 3
        coeff = DICE["minus3"]
    elif choice == "6":
        win = value == 6
        coeff = DICE["6"]
    else:
        raise ValueError("bad choice")
    return win, coeff, value
