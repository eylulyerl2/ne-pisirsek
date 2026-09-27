import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_plan_for_user
from app.models import Profile
from app.schemas.shopping import ShoppingItemResponse, ShoppingItemUpdate, ShoppingListResponse
from app.services.shopping import load_shopping_list, rebuild_shopping_list, shopping_list_response

router = APIRouter(prefix="/plans/{plan_id}/shopping-list", tags=["shopping"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu plan için alışveriş listesi yok")


@router.post("", response_model=ShoppingListResponse)
def build_shopping_list(
    plan_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan_for_user(db, plan_id, current_user)
    shopping_list = rebuild_shopping_list(db, plan)
    if shopping_list is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan boş, önce yemek ekleyin")
    return shopping_list_response(shopping_list)


@router.get("", response_model=ShoppingListResponse)
def get_shopping_list(
    plan_id: uuid.UUID,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shopping_list = load_shopping_list(db, get_plan_for_user(db, plan_id, current_user))
    if shopping_list is None:
        raise _not_found()
    return shopping_list_response(shopping_list)


@router.patch("/items/{item_id}", response_model=ShoppingItemResponse)
def check_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ShoppingItemUpdate,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shopping_list = load_shopping_list(db, get_plan_for_user(db, plan_id, current_user))
    if shopping_list is None:
        raise _not_found()
    item = next((i for i in shopping_list.items if i.item_id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ürün bulunamadı")
    item.is_checked = payload.is_checked
    db.commit()
    return next(i for i in shopping_list_response(shopping_list).items if i.item_id == item_id)
