from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import calc_macro_targets, DEFAULT_DAILY_CALORIE_TARGET
from ..database import get_db
from ..models import DietRecord, UserProfile
from ..schemas import (
    DailyCalorie,
    DietRecordRequest,
    DietRecordResponse,
    MealGroup,
    TodaySummaryResponse,
    WeeklyResponse,
)
from ..services.food_kb import get_food_by_name
from ..services.nutrition import calc_nutrients

router = APIRouter(prefix="/api/v1/diet", tags=["diet"])


def _get_user_target(db: Session) -> float:
    profile = db.query(UserProfile).order_by(UserProfile.id.desc()).first()
    if profile:
        return profile.daily_calorie_target
    return DEFAULT_DAILY_CALORIE_TARGET


@router.post("/record", response_model=DietRecordResponse)
def record_diet(req: DietRecordRequest, db: Session = Depends(get_db)):
    food = get_food_by_name(db, req.food_name)
    if not food:
        raise HTTPException(status_code=404, detail=f"未找到食物\"{req.food_name}\"，请先使用AI识别")

    nutrients = calc_nutrients(food, req.amount_g)
    record = DietRecord(
        meal_type=req.meal_type,
        food_name=req.food_name,
        amount_g=req.amount_g,
        calories=nutrients["calories"],
        protein_g=nutrients["protein_g"],
        carbs_g=nutrients["carbs_g"],
        fat_g=nutrients["fat_g"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_to_response(record)


@router.get("/today", response_model=TodaySummaryResponse)
def get_today(db: Session = Depends(get_db)):
    today = date.today()
    records = (
        db.query(DietRecord)
        .filter(func.date(DietRecord.created_at) == today)
        .order_by(DietRecord.created_at.desc())
        .all()
    )
    daily_target = _get_user_target(db)
    macros = calc_macro_targets(int(daily_target))

    meal_order = {"早餐": 0, "午餐": 1, "晚餐": 2, "加餐": 3}
    groups: dict[str, list] = {}
    for r in records:
        groups.setdefault(r.meal_type, []).append(r)
    meals = [
        MealGroup(
            meal_type=mt,
            items=[_record_to_response(r) for r in items],
            subtotal_calories=round(sum(r.calories for r in items), 1),
        )
        for mt, items in sorted(groups.items(), key=lambda x: meal_order.get(x[0], 99))
    ]

    total_cal = round(sum(r.calories for r in records), 1)
    total_p = round(sum(r.protein_g for r in records), 1)
    total_c = round(sum(r.carbs_g for r in records), 1)
    total_f = round(sum(r.fat_g for r in records), 1)

    return TodaySummaryResponse(
        date=today.isoformat(),
        meals=meals,
        total_calories=total_cal,
        total_protein_g=total_p,
        total_carbs_g=total_c,
        total_fat_g=total_f,
        daily_target=daily_target,
        surplus=round(total_cal - daily_target, 1),
        protein_goal_g=macros["protein_g"],
        protein_surplus=round(total_p - macros["protein_g"], 1),
        carbs_goal_g=macros["carbs_g"],
        carbs_surplus=round(total_c - macros["carbs_g"], 1),
        fat_goal_g=macros["fat_g"],
        fat_surplus=round(total_f - macros["fat_g"], 1),
    )


@router.get("/weekly", response_model=WeeklyResponse)
def get_weekly(db: Session = Depends(get_db)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    daily_target = _get_user_target(db)

    daily_calories = []
    total_all = 0.0
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_cal = (
            db.query(func.coalesce(func.sum(DietRecord.calories), 0))
            .filter(func.date(DietRecord.created_at) == d)
            .scalar()
        )
        daily_calories.append(DailyCalorie(date=d.isoformat(), total=round(float(day_cal), 1)))
        total_all += float(day_cal)

    return WeeklyResponse(
        week_start=week_start.isoformat(),
        daily_calories=daily_calories,
        avg_daily=round(total_all / 7, 1),
        target_line=daily_target,
    )


@router.delete("/record/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(DietRecord).filter(DietRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}


def _record_to_response(r: DietRecord) -> DietRecordResponse:
    return DietRecordResponse(
        id=r.id,
        meal_type=r.meal_type,
        food_name=r.food_name,
        amount_g=r.amount_g,
        calories=r.calories,
        protein_g=r.protein_g,
        carbs_g=r.carbs_g,
        fat_g=r.fat_g,
        meal_score=r.meal_score,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )
