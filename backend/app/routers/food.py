import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import FoodRecognizeRequest, FoodRecognizeResponse, FoodSearchItem
from ..services.ai_engine import build_system_prompt, chat
from ..services.food_kb import get_food_by_name, search_food
from ..services.nutrition import calc_nutrients

router = APIRouter(prefix="/api/v1/food", tags=["food"])


@router.post("/recognize", response_model=FoodRecognizeResponse)
async def recognize_food(req: FoodRecognizeRequest, db: Session = Depends(get_db)):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="请输入食物描述")

    # Parse amount from query (e.g., "一个苹果约200克", "150克鸡胸肉")
    amount_g = 200.0
    amount_match = re.search(r"(\d+)\s*克", query)
    if amount_match:
        amount_g = float(amount_match.group(1))

    # Try local knowledge base first
    food = get_food_by_name(db, query)
    if food:
        nutrients = calc_nutrients(food, amount_g)
        return FoodRecognizeResponse(
            food_name=food["food_name"],
            category=food["category"],
            amount_g=amount_g,
            calories=nutrients["calories"],
            protein_g=nutrients["protein_g"],
            carbs_g=nutrients["carbs_g"],
            fat_g=nutrients["fat_g"],
            confidence=0.85,
        )

    # Fall back to AI recognition
    try:
        system = build_system_prompt("nutritionist")
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"用户输入了食物描述：\"{query}\"\n"
                "请识别食物并返回JSON格式（只返回JSON，不要其他文字）：\n"
                "{\n"
                '  "food_name": "食物名称",\n'
                '  "category": "分类(主食/肉类/水产/蛋奶豆/蔬菜/水果/零食饮料/中式菜肴)",\n'
                '  "amount_g": 克数,\n'
                '  "calories_per_100g": 每100克热量,\n'
                '  "protein_per_100g": 每100克蛋白质克数,\n'
                '  "carbs_per_100g": 每100克碳水克数,\n'
                '  "fat_per_100g": 每100克脂肪克数\n'
                "}"
            )},
        ]
        result = await chat(messages, temperature=0.3, max_tokens=512)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("\n", 1)[0]
        data = json.loads(result)
        food_data = {
            "food_name": data["food_name"],
            "category": data.get("category", "其他"),
            "calories_per_100g": data["calories_per_100g"],
            "protein_per_100g": data.get("protein_per_100g", 0),
            "carbs_per_100g": data.get("carbs_per_100g", 0),
            "fat_per_100g": data.get("fat_per_100g", 0),
        }
        nutrients = calc_nutrients(food_data, amount_g)
        return FoodRecognizeResponse(
            food_name=food_data["food_name"],
            category=food_data["category"],
            amount_g=amount_g,
            calories=nutrients["calories"],
            protein_g=nutrients["protein_g"],
            carbs_g=nutrients["carbs_g"],
            fat_g=nutrients["fat_g"],
            confidence=0.90,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"食物识别失败: {str(e)}")


@router.get("/search", response_model=list[FoodSearchItem])
def search_foods(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    results = search_food(db, keyword)
    if not results:
        from ..services.food_kb import _load_food_knowledge
        kb = _load_food_knowledge()
        for name, data in kb.items():
            if keyword in name:
                results.append(data)
    return results
