import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, get_membership, get_plan_for_user
from app.models import Meal, PlannedMeal, Profile, WeeklyPlan
from app.schemas.plan import (
    AlternativeMeal,
    GenerateRequest,
    GenerateResponse,
    PlanCreate,
    PlanDetail,
    PlannedMealCreate,
    PlannedMealResponse,
    PlannedMealUpdate,
    PlanStatus,
    PlanStatusUpdate,
    PlanSummary,
    ReplaceRequest,
)
from app.services.planning import (
    default_servings,
    generate_plan_meals,
    plan_detail,
    planned_meal_response,
    suggest_alternatives,
)

router = APIRouter(prefix="/plans", tags=["plans"])

DUPLICATE_PLAN = "Bu hafta için zaten bir plan var"


def _summary(plan: WeeklyPlan) -> PlanSummary:
    return PlanSummary(
        plan_id=plan.plan_id,
        user_id=plan.user_id,
        family_id=plan.family_id,
        week_start_date=plan.week_start_date,
        status=plan.status,
        created_at=plan.created_at,
    )


def _require_active_meal(db: Session, meal_id: uuid.UUID) -> None:
    if db.query(Meal.meal_id).filter(Meal.meal_id == meal_id, Meal.is_active.is_(True)).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yemek bulunamadı")


def _get_planned_meal(db: Session, plan: WeeklyPlan, planned_meal_id: uuid.UUID) -> PlannedMeal:
    planned = (
        db.query(PlannedMeal)
        .options(
            selectinload(PlannedMeal.meal).selectinload(Meal.categories),
            selectinload(PlannedMeal.meal).selectinload(Meal.nutrition),
        )
        .filter(PlannedMeal.planned_meal_id == planned_meal_id, PlannedMeal.plan_id == plan.plan_id)
        .first()
    )
    if planned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planlanmış yemek bulunamadı")
    return planned


@router.post("", response_model=PlanSummary, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.family_id is not None:
        get_membership(db, payload.family_id, current_user)
        owner = {"family_id": payload.family_id}
        existing = WeeklyPlan.family_id == payload.family_id
    else:
        owner = {"user_id": current_user.user_id}
        existing = WeeklyPlan.user_id == current_user.user_id

    if db.query(WeeklyPlan.plan_id).filter(existing, WeeklyPlan.week_start_date == payload.week_start_date).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_PLAN)

    plan = WeeklyPlan(week_start_date=payload.week_start_date, **owner)
    db.add(plan)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_PLAN)
    db.refresh(plan)
    return _summary(plan)


@router.get("", response_model=list[PlanSummary])
def list_plans(
    family_id: uuid.UUID | None = Query(None, description="Verilmezse kişisel planlar listelenir"),
    plan_status: PlanStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if family_id is not None:
        get_membership(db, family_id, current_user)
        query = db.query(WeeklyPlan).filter(WeeklyPlan.family_id == family_id)
    else:
        query = db.query(WeeklyPlan).filter(WeeklyPlan.user_id == current_user.user_id)
    if plan_status is not None:
        query = query.filter(WeeklyPlan.status == plan_status)
    plans = query.order_by(WeeklyPlan.week_start_date.desc()).limit(limit).offset(offset).all()
    return [_summary(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanDetail)
def get_plan(plan_id: uuid.UUID, current_user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return plan_detail(db, get_plan_for_user(db, plan_id, current_user))


@router.patch("/{plan_id}", response_model=PlanSummary)
def update_plan_status(
    plan_id: uuid.UUID,
    payload: PlanStatusUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    plan.status = payload.status
    db.commit()
    db.refresh(plan)
    return _summary(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: uuid.UUID, current_user: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = get_plan_for_user(db, plan_id, current_user, require_admin=True)
    db.delete(plan)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{plan_id}/generate", response_model=GenerateResponse)
def generate_plan(
    plan_id: uuid.UUID,
    payload: GenerateRequest | None = None,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = payload or GenerateRequest()
    plan = get_plan_for_user(db, plan_id, current_user)
    result = generate_plan_meals(
        db, plan, payload.meal_types, payload.seed, compose=payload.compose, exclude_ids=payload.exclude_meal_ids
    )
    return GenerateResponse(plan=plan_detail(db, plan), warnings=result.warnings)


@router.post("/{plan_id}/meals", response_model=PlannedMealResponse, status_code=status.HTTP_201_CREATED)
def add_planned_meal(
    plan_id: uuid.UUID,
    payload: PlannedMealCreate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    _require_active_meal(db, payload.meal_id)
    planned = PlannedMeal(
        plan_id=plan.plan_id,
        meal_id=payload.meal_id,
        day_of_week=payload.day_of_week,
        meal_type=payload.meal_type,
        course=payload.course,
        servings=payload.servings or default_servings(db, plan),
    )
    db.add(planned)
    db.commit()
    return planned_meal_response(_get_planned_meal(db, plan, planned.planned_meal_id))


@router.get("/{plan_id}/meals/{planned_meal_id}/alternatives", response_model=list[AlternativeMeal])
def list_alternatives(
    plan_id: uuid.UUID,
    planned_meal_id: uuid.UUID,
    limit: int = Query(6, ge=1, le=20),
    seed: int | None = None,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    planned = _get_planned_meal(db, plan, planned_meal_id)
    return suggest_alternatives(db, plan, planned, limit=limit, seed=seed)


@router.post("/{plan_id}/meals/{planned_meal_id}/replace", response_model=PlannedMealResponse)
def replace_planned_meal(
    plan_id: uuid.UUID,
    planned_meal_id: uuid.UUID,
    payload: ReplaceRequest | None = None,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = payload or ReplaceRequest()
    plan = get_plan_for_user(db, plan_id, current_user)
    planned = _get_planned_meal(db, plan, planned_meal_id)
    if payload.meal_id is not None:
        _require_active_meal(db, payload.meal_id)
        new_meal_id = payload.meal_id
    else:
        alternatives = suggest_alternatives(db, plan, planned, limit=1, seed=payload.seed)
        if not alternatives:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Uygun bir alternatif bulunamadı")
        new_meal_id = alternatives[0].meal_id
    planned.meal_id = new_meal_id
    planned.is_completed = False
    db.commit()
    return planned_meal_response(_get_planned_meal(db, plan, planned_meal_id))


@router.patch("/{plan_id}/meals/{planned_meal_id}", response_model=PlannedMealResponse)
def update_planned_meal(
    plan_id: uuid.UUID,
    planned_meal_id: uuid.UUID,
    payload: PlannedMealUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    planned = _get_planned_meal(db, plan, planned_meal_id)
    changes = payload.model_dump(exclude_unset=True)
    if "meal_id" in changes:
        _require_active_meal(db, changes["meal_id"])
    for field, value in changes.items():
        setattr(planned, field, value)
    db.commit()
    return planned_meal_response(_get_planned_meal(db, plan, planned_meal_id))


@router.delete("/{plan_id}/meals/{planned_meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_meal(
    plan_id: uuid.UUID,
    planned_meal_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    db.delete(_get_planned_meal(db, plan, planned_meal_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
