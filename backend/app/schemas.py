from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---- Food Recognition ----
class FoodRecognizeRequest(BaseModel):
    query: str


class FoodRecognizeResponse(BaseModel):
    food_name: str
    category: str
    amount_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float


# ---- Food Search ----
class FoodSearchItem(BaseModel):
    food_name: str
    category: str
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    typical_portion_g: float


# ---- Diet Record ----
class DietRecordRequest(BaseModel):
    meal_type: str = Field(..., description="早餐/午餐/晚餐/加餐")
    food_name: str
    amount_g: float


class DietRecordResponse(BaseModel):
    id: int
    meal_type: str
    food_name: str
    amount_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    meal_score: Optional[int] = None
    created_at: str


class MealGroup(BaseModel):
    meal_type: str
    items: list[DietRecordResponse]
    subtotal_calories: float


class TodaySummaryResponse(BaseModel):
    date: str
    meals: list[MealGroup]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    daily_target: float
    surplus: float
    protein_goal_g: float
    protein_surplus: float
    carbs_goal_g: float
    carbs_surplus: float
    fat_goal_g: float
    fat_surplus: float


# ---- Weekly ----
class DailyCalorie(BaseModel):
    date: str
    total: float


class WeeklyResponse(BaseModel):
    week_start: str
    daily_calories: list[DailyCalorie]
    avg_daily: float
    target_line: float


# ---- AI Analyze ----
class AIAnalyzeResponse(BaseModel):
    summary: str
    issues: list[str]
    suggestions: list[str]
    score: int


# ---- AI Score ----
class FoodItem(BaseModel):
    food_name: str
    amount_g: float


class AIScoreRequest(BaseModel):
    meal_type: str
    foods: list[FoodItem]


class AIScoreResponse(BaseModel):
    score: int
    good_points: list[str]
    bad_points: list[str]
    improvement: str


# ---- AI Chat ----
class AIChatRequest(BaseModel):
    message: str
    user_context: str = ""


class AIChatResponse(BaseModel):
    reply: str


# ---- User Profile ----
class UserProfileRequest(BaseModel):
    height_cm: float
    weight_kg: float
    target_weight_kg: float = 65
    daily_calorie_target: float = 1800


class UserProfileResponse(BaseModel):
    id: int
    height_cm: float
    weight_kg: float
    target_weight_kg: float
    daily_calorie_target: float
    bmi: float
    created_at: str
