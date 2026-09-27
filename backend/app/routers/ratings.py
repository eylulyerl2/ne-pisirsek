import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Meal, MealRating, Profile
from app.schemas.rating import MyRatingResponse, RatingResponse, RatingUpsert

router = APIRouter(tags=["ratings"])


def _require_active_meal(db: Session, meal_id: uuid.UUID) -> None:
    exists = db.query(Meal.meal_id).filter(Meal.meal_id == meal_id, Meal.is_active.is_(True)).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yemek bulunamadı")


@router.put("/meals/{meal_id}/rating", response_model=RatingResponse)
def rate_meal(
    meal_id: uuid.UUID,
    payload: RatingUpsert,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_active_meal(db, meal_id)
    stmt = insert(MealRating).values(
        user_id=current_user.user_id, meal_id=meal_id, rating=payload.rating, comment=payload.comment
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_meal_ratings_user_meal",
        set_={"rating": stmt.excluded.rating, "comment": stmt.excluded.comment, "updated_at": func.now()},
    ).returning(MealRating)
    rating = db.scalars(stmt).one()
    db.commit()
    return rating


@router.get("/meals/{meal_id}/rating", response_model=RatingResponse)
def get_my_rating(
    meal_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rating = (
        db.query(MealRating)
        .filter(MealRating.meal_id == meal_id, MealRating.user_id == current_user.user_id)
        .first()
    )
    if rating is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu yemeği henüz puanlamadınız")
    return rating


@router.delete("/meals/{meal_id}/rating", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_rating(
    meal_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(MealRating)
        .filter(MealRating.meal_id == meal_id, MealRating.user_id == current_user.user_id)
        .delete(synchronize_session=False)
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu yemeği henüz puanlamadınız")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me/ratings", response_model=list[MyRatingResponse])
def list_my_ratings(current_user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(MealRating, Meal.name)
        .join(Meal, Meal.meal_id == MealRating.meal_id)
        .filter(MealRating.user_id == current_user.user_id)
        .order_by(MealRating.updated_at.desc())
        .all()
    )
    return [
        MyRatingResponse(**RatingResponse.model_validate(rating).model_dump(), meal_name=meal_name)
        for rating, meal_name in rows
    ]
