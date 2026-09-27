import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import collate, func
from sqlalchemy.orm import Session, selectinload

from app.constants import REGIONS
from app.database import get_db
from app.models import Category, Meal, MealIngredient, MealRating
from app.schemas.meal import (
    CategoryResponse,
    IngredientResponse,
    MealDetail,
    MealListResponse,
    MealSummary,
    RegionResponse,
)

router = APIRouter(tags=["meals"])

RegionSlug = Literal[tuple(REGIONS)]

TR_COLLATION = "tr-TR-x-icu"


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(collate(Category.name, TR_COLLATION)).all()


@router.get("/regions", response_model=list[RegionResponse])
def list_regions():
    return [RegionResponse(slug=slug, name=name) for slug, name in REGIONS.items()]


@router.get("/meals", response_model=MealListResponse)
def list_meals(
    q: str | None = Query(None, max_length=100, description="Yemek adinda arama"),
    category: list[str] | None = Query(None, description="Kategori slug'i (birden fazla verilebilir)"),
    region: list[RegionSlug] | None = Query(None, description="Bölge slug'i (birden fazla verilebilir)"),
    max_time_minutes: int | None = Query(None, ge=0, description="Hazirlik + pisirme suresi ust siniri"),
    max_cost: float | None = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Meal).filter(Meal.is_active.is_(True))

    if q:
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(Meal.name.ilike(pattern, escape="\\"))
    if category:
        query = query.filter(Meal.categories.any(Category.slug.in_(category)))
    if region:
        query = query.filter(Meal.region.in_(region))
    if max_time_minutes is not None:
        total_time = func.coalesce(Meal.preparation_time_minutes, 0) + func.coalesce(Meal.cooking_time_minutes, 0)
        query = query.filter(total_time <= max_time_minutes)
    if max_cost is not None:
        query = query.filter(Meal.estimated_cost <= max_cost)

    total = query.count()
    items = (
        query.options(selectinload(Meal.categories), selectinload(Meal.nutrition))
        .order_by(collate(Meal.name, TR_COLLATION), Meal.meal_id)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return MealListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/meals/{meal_id}", response_model=MealDetail)
def get_meal(meal_id: uuid.UUID, db: Session = Depends(get_db)):
    meal = (
        db.query(Meal)
        .options(
            selectinload(Meal.categories),
            selectinload(Meal.nutrition),
            selectinload(Meal.ingredients).selectinload(MealIngredient.ingredient),
        )
        .filter(Meal.meal_id == meal_id, Meal.is_active.is_(True))
        .first()
    )
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yemek bulunamadı")

    avg_rating, rating_count = (
        db.query(func.avg(MealRating.rating), func.count(MealRating.rating_id))
        .filter(MealRating.meal_id == meal_id)
        .one()
    )
    summary = MealSummary.model_validate(meal).model_dump(exclude={"total_time_minutes", "region_name"})
    return MealDetail(
        **summary,
        instructions=meal.instructions,
        source_type=meal.source_type,
        source_url=meal.source_url,
        ingredients=[
            IngredientResponse(
                name=mi.ingredient.name, quantity=mi.quantity, unit=mi.unit, is_optional=mi.is_optional
            )
            for mi in sorted(meal.ingredients, key=lambda mi: mi.ingredient.name)
        ],
        average_rating=round(float(avg_rating), 2) if avg_rating is not None else None,
        rating_count=rating_count,
    )
