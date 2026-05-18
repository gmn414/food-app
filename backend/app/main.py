from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import SessionLocal, engine
from .models import Base
from .routers import ai, diet, food
from .services.food_kb import seed_food_knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = seed_food_knowledge(db)
        if count > 0:
            print(f"Seeded {count} food knowledge entries")
    finally:
        db.close()
    yield


app = FastAPI(
    title="AI减脂营养师 API",
    description="面向减脂人群的AI饮食记录与营养分析工具",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(food.router)
app.include_router(diet.router)
app.include_router(ai.router)


@app.get("/api/v1/user/profile")
def get_profile():
    from .models import UserProfile
    from .schemas import UserProfileResponse
    db = SessionLocal()
    try:
        profile = db.query(UserProfile).order_by(UserProfile.id.desc()).first()
        if not profile:
            return None
        height_m = profile.height_cm / 100
        bmi = round(profile.weight_kg / (height_m ** 2), 1)
        return UserProfileResponse(
            id=profile.id,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            target_weight_kg=profile.target_weight_kg,
            daily_calorie_target=profile.daily_calorie_target,
            bmi=bmi,
            created_at=profile.created_at.isoformat() if profile.created_at else "",
        )
    finally:
        db.close()


@app.post("/api/v1/user/profile")
def save_profile(profile_data: dict, db=None):
    from datetime import datetime
    from .models import UserProfile
    real_db = SessionLocal()
    try:
        existing = real_db.query(UserProfile).order_by(UserProfile.id.desc()).first()
        if existing:
            existing.height_cm = profile_data.get("height_cm", existing.height_cm)
            existing.weight_kg = profile_data.get("weight_kg", existing.weight_kg)
            existing.target_weight_kg = profile_data.get("target_weight_kg", existing.target_weight_kg)
            existing.daily_calorie_target = profile_data.get("daily_calorie_target", existing.daily_calorie_target)
        else:
            new_profile = UserProfile(
                height_cm=profile_data.get("height_cm", 170),
                weight_kg=profile_data.get("weight_kg", 70),
                target_weight_kg=profile_data.get("target_weight_kg", 65),
                daily_calorie_target=profile_data.get("daily_calorie_target", 1800),
            )
            real_db.add(new_profile)
        real_db.commit()
        return {"ok": True}
    finally:
        real_db.close()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "AI减脂营养师"}
