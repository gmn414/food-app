import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..models import FoodKnowledge

_FOOD_CACHE: Optional[dict[str, dict]] = None


def _load_food_knowledge() -> dict[str, dict]:
    global _FOOD_CACHE
    if _FOOD_CACHE is None:
        kb_path = Path(__file__).resolve().parent.parent.parent / "food_knowledge.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            foods = json.load(f)
        _FOOD_CACHE = {item["food_name"]: item for item in foods}
    return _FOOD_CACHE


def seed_food_knowledge(db: Session) -> int:
    kb = _load_food_knowledge()
    count = 0
    for name, data in kb.items():
        existing = db.query(FoodKnowledge).filter(FoodKnowledge.food_name == name).first()
        if not existing:
            db.add(FoodKnowledge(
                food_name=data["food_name"],
                category=data["category"],
                calories_per_100g=data["calories_per_100g"],
                protein_per_100g=data["protein_per_100g"],
                carbs_per_100g=data["carbs_per_100g"],
                fat_per_100g=data["fat_per_100g"],
                typical_portion_g=data["typical_portion_g"],
            ))
            count += 1
    db.commit()
    return count


def search_food(db: Session, keyword: str, limit: int = 20) -> list[dict]:
    query = db.query(FoodKnowledge).filter(
        FoodKnowledge.food_name.contains(keyword)
    ).limit(limit).all()
    return [_food_to_dict(f) for f in query]


def get_food_by_name(db: Session, food_name: str) -> Optional[dict]:
    food = db.query(FoodKnowledge).filter(FoodKnowledge.food_name == food_name).first()
    if not food:
        food = db.query(FoodKnowledge).filter(
            FoodKnowledge.food_name.contains(food_name)
        ).first()
    if not food:
        kb = _load_food_knowledge()
        data = kb.get(food_name)
        if data:
            return data
        for name, data in kb.items():
            if food_name in name or name in food_name:
                return data
    return _food_to_dict(food) if food else None


def _food_to_dict(food: FoodKnowledge) -> dict:
    return {
        "food_name": food.food_name,
        "category": food.category,
        "calories_per_100g": food.calories_per_100g,
        "protein_per_100g": food.protein_per_100g,
        "carbs_per_100g": food.carbs_per_100g,
        "fat_per_100g": food.fat_per_100g,
        "typical_portion_g": food.typical_portion_g,
    }
