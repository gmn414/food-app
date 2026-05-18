import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./food_app.db")
DEFAULT_DAILY_CALORIE_TARGET = int(os.getenv("DAILY_CALORIE_TARGET", "1800"))
_DEFAULT_API_KEY = "sk-41e5979d46124c579634191a5f51ed92"
DEEPSEEK_API_KEY = _DEFAULT_API_KEY if _DEFAULT_API_KEY else os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
AI_TIMEOUT_SECONDS = 30
AI_MAX_RETRIES = 3

MACRO_RATIO = {"protein": 0.30, "carbs": 0.45, "fat": 0.25}


def calc_macro_targets(daily_calories: int):
    return {
        "protein_g": round(daily_calories * MACRO_RATIO["protein"] / 4),
        "carbs_g": round(daily_calories * MACRO_RATIO["carbs"] / 4),
        "fat_g": round(daily_calories * MACRO_RATIO["fat"] / 9),
    }
