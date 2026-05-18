from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class DietRecord(Base):
    __tablename__ = "diet_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_type = Column(String, nullable=False)
    food_name = Column(String, nullable=False)
    amount_g = Column(Float, nullable=False)
    calories = Column(Float, nullable=False, default=0)
    protein_g = Column(Float, nullable=False, default=0)
    carbs_g = Column(Float, nullable=False, default=0)
    fat_g = Column(Float, nullable=False, default=0)
    meal_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    target_weight_kg = Column(Float, nullable=False)
    daily_calorie_target = Column(Float, nullable=False, default=1800)
    created_at = Column(DateTime, default=func.now())


class FoodKnowledge(Base):
    __tablename__ = "food_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    calories_per_100g = Column(Float, nullable=False)
    protein_per_100g = Column(Float, nullable=False, default=0)
    carbs_per_100g = Column(Float, nullable=False, default=0)
    fat_per_100g = Column(Float, nullable=False, default=0)
    typical_portion_g = Column(Float, nullable=False, default=100)
