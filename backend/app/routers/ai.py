import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import calc_macro_targets
from ..database import get_db
from ..models import DietRecord, UserProfile
from ..schemas import (
    AIChatRequest,
    AIChatResponse,
    AIAnalyzeResponse,
    AIScoreRequest,
    AIScoreResponse,
)
from ..services.ai_engine import build_system_prompt, chat, is_api_available
from ..routers.diet import _get_user_target

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def _get_today_nutrition(db: Session) -> dict:
    today = date.today()
    records = (
        db.query(DietRecord)
        .filter(func.date(DietRecord.created_at) == today)
        .all()
    )
    total_cal = round(sum(r.calories for r in records), 1)
    total_p = round(sum(r.protein_g for r in records), 1)
    total_c = round(sum(r.carbs_g for r in records), 1)
    total_f = round(sum(r.fat_g for r in records), 1)

    meals_by_type: dict[str, list] = {}
    for r in records:
        meals_by_type.setdefault(r.meal_type, []).append({
            "food_name": r.food_name,
            "amount_g": r.amount_g,
            "calories": r.calories,
        })

    daily_target = _get_user_target(db)
    macros = calc_macro_targets(int(daily_target))

    return {
        "total_calories": total_cal,
        "total_protein_g": total_p,
        "total_carbs_g": total_c,
        "total_fat_g": total_f,
        "daily_target": daily_target,
        "protein_target": macros["protein_g"],
        "carbs_target": macros["carbs_g"],
        "fat_target": macros["fat_g"],
        "meals": meals_by_type,
        "records": [
            f"{r.meal_type}: {r.food_name} {r.amount_g}g ({r.calories}千卡)"
            for r in records
        ],
    }


def _get_user_profile(db: Session) -> dict | None:
    profile = db.query(UserProfile).order_by(UserProfile.id.desc()).first()
    if not profile:
        return None
    return {
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "target_weight_kg": profile.target_weight_kg,
        "daily_calorie_target": profile.daily_calorie_target,
    }


@router.post("/analyze", response_model=AIAnalyzeResponse)
async def analyze_diet(db: Session = Depends(get_db)):
    nutrition = _get_today_nutrition(db)
    profile = _get_user_profile(db)

    if not nutrition["records"]:
        raise HTTPException(status_code=400, detail="今日暂无饮食记录")

    system = build_system_prompt("nutritionist")
    profile_str = ""
    if profile:
        profile_str = (
            f"用户信息：身高{profile['height_cm']}cm，体重{profile['weight_kg']}kg，"
            f"目标体重{profile['target_weight_kg']}kg\n"
        )

    prompt = (
        f"{profile_str}"
        f"今日饮食记录：\n"
        + "\n".join(nutrition["records"])
        + f"\n\n"
        f"摄入汇总：热量{nutrition['total_calories']}千卡（目标{nutrition['daily_target']}千卡），"
        f"蛋白质{nutrition['total_protein_g']}g（目标{nutrition['protein_target']}g），"
        f"碳水{nutrition['total_carbs_g']}g，脂肪{nutrition['total_fat_g']}g\n\n"
        f"请分析今日饮食并返回JSON格式（只返回JSON）：\n"
        f'{{"summary":"总体评价一句话","issues":["问题1","问题2","问题3"],'
        f'"suggestions":["建议1","建议2","建议3"],"score": 1-10的整数}}'
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    result = await chat(messages, temperature=0.7, max_tokens=1024)
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("\n", 1)[0]

    try:
        data = json.loads(result)
    except (json.JSONDecodeError, KeyError):
        data = {
            "summary": f"今日摄入{nutrition['total_calories']}千卡",
            "issues": [],
            "suggestions": [],
            "score": 5,
        }

    return AIAnalyzeResponse(
        summary=data.get("summary", ""),
        issues=data.get("issues", []),
        suggestions=data.get("suggestions", []),
        score=int(data.get("score", 5)),
    )


@router.post("/score", response_model=AIScoreResponse)
async def score_meal(req: AIScoreRequest):
    foods_desc = "\n".join(
        f"- {f.food_name}: {f.amount_g}g" for f in req.foods
    )
    system = build_system_prompt("nutritionist")
    prompt = (
        f"请评估这顿{req.meal_type}的减脂友好程度：\n"
        f"{foods_desc}\n\n"
        "返回JSON格式（只返回JSON）：\n"
        '{"score": 1-10的整数,"good_points":["优点"],"bad_points":["缺点"],'
        '"improvement":"一句话改进建议"}'
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    result = await chat(messages, temperature=0.5, max_tokens=512)
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("\n", 1)[0]

    try:
        data = json.loads(result)
    except (json.JSONDecodeError, KeyError):
        data = {
            "score": 5,
            "good_points": ["已记录本餐"],
            "bad_points": [],
            "improvement": "持续记录有助于获得更精准的建议",
        }

    return AIScoreResponse(
        score=int(data.get("score", 5)),
        good_points=data.get("good_points", []),
        bad_points=data.get("bad_points", []),
        improvement=data.get("improvement", ""),
    )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="请输入消息")

    profile = _get_user_profile(db)
    profile_context = req.user_context or ""
    if profile and not req.user_context:
        profile_context = (
            f"身高{profile['height_cm']}cm，体重{profile['weight_kg']}kg，"
            f"目标体重{profile['target_weight_kg']}kg，"
            f"日目标{profile['daily_calorie_target']}千卡"
        )

    nutrition = _get_today_nutrition(db)
    diet_context = ""
    if nutrition["records"]:
        diet_context = (
            f"\n今日已摄入：热量{nutrition['total_calories']}千卡/"
            f"目标{nutrition['daily_target']}千卡，"
            f"蛋白质{nutrition['total_protein_g']}g/"
            f"目标{nutrition['protein_target']}g，"
            f"碳水{nutrition['total_carbs_g']}g，脂肪{nutrition['total_fat_g']}g\n"
            f"今日饮食：" + "；".join(nutrition["records"])
        )

    system = build_system_prompt("nutritionist")
    system += f"\n\n当前用户资料：{profile_context}{diet_context}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": req.message},
    ]
    reply = await chat(messages, temperature=0.7, max_tokens=1024)

    if not is_api_available():
        reply += "\n\n💡 当前回复由本地营养引擎生成（API暂不可用），内容基于84种食物知识库，建议同样有效。"

    return AIChatResponse(reply=reply)
