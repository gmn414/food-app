def calc_nutrients(food_data: dict, amount_g: float) -> dict:
    per100 = 100.0
    ratio = amount_g / per100
    return {
        "calories": round(food_data["calories_per_100g"] * ratio, 1),
        "protein_g": round(food_data["protein_per_100g"] * ratio, 1),
        "carbs_g": round(food_data["carbs_per_100g"] * ratio, 1),
        "fat_g": round(food_data["fat_per_100g"] * ratio, 1),
    }
