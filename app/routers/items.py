from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas.item import ProductCreate, ProductUpdate
from services import shopping_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    return shopping_service.add_product(db, product.name, product.category, product.quantity)


@router.get("")
def read_products(category: str | None = None, bought: bool | None = None, db: Session = Depends(get_db)):
    return shopping_service.list_products(db, category=category, bought=bought)


@router.get("/{product_id}")
def read_product(product_id: int, db: Session = Depends(get_db)):
    return shopping_service.get_product(db, product_id)


@router.patch("/{product_id}")
def update_product(product_id: int, update: ProductUpdate, db: Session = Depends(get_db)):
    return shopping_service.update_product(db, product_id, quantity=update.quantity, bought=update.bought)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    shopping_service.delete_product(db, product_id)


@router.post("/{product_id}/favorite")
def add_favorite(product_id: int, db: Session = Depends(get_db)):
    return shopping_service.add_favorite(db, product_id)


@router.delete("/{product_id}/favorite")
def remove_favorite(product_id: int, db: Session = Depends(get_db)):
    return shopping_service.remove_favorite(db, product_id)


@router.post("/from-favorites", status_code=201)
def add_from_favorites(db: Session = Depends(get_db)):
    return shopping_service.add_from_favorites(db)


@router.get("/categories", tags=["categories"])
def list_categories():
    return shopping_service.CATEGORIES


@router.get("/favorites", tags=["favorites"])
def read_favorites(db: Session = Depends(get_db)):
    return shopping_service.list_favorites(db)


@router.get("/history", tags=["history"])
def read_history(db: Session = Depends(get_db)):
    return shopping_service.list_history(db)
