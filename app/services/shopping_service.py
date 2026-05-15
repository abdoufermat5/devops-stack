from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.item import Product, HistoryEntry, Favorite


CATEGORIES = ["legumes", "boissons", "hygiene", "fruits", "viandes", "produits-laitiers", "epicerie", "autre"]


def list_products(db: Session, category: str | None = None, bought: bool | None = None) -> list[Product]:
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if bought is not None:
        query = query.filter(Product.bought == bought)
    return query.all()


def get_product(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product


def add_product(db: Session, name: str, category: str, quantity: int) -> Product:
    existing = db.query(Product).filter(Product.name.ilike(name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Produit déjà existant")

    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Catégorie invalide. Choisissez parmi: {CATEGORIES}")

    product = Product(name=name, category=category, quantity=quantity, bought=False)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, quantity: int | None = None, bought: bool | None = None) -> Product:
    product = get_product(db, product_id)

    if quantity is not None:
        if product.quantity > 0 and quantity == 0:
            history = HistoryEntry(
                product_name=product.name,
                quantity=product.quantity,
                timestamp=datetime.utcnow(),
            )
            db.add(history)
        product.quantity = quantity

    if bought is not None:
        product.bought = bought

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()


def add_favorite(db: Session, product_id: int) -> dict:
    product = get_product(db, product_id)

    existing = db.query(Favorite).filter(Favorite.product_name == product.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Déjà en favoris")

    favorite = Favorite(product_name=product.name)
    db.add(favorite)
    db.commit()
    return {"message": "Ajouté aux favoris"}


def remove_favorite(db: Session, product_id: int) -> dict:
    product = get_product(db, product_id)

    favorite = db.query(Favorite).filter(Favorite.product_name == product.name).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Pas en favoris")

    db.delete(favorite)
    db.commit()
    return {"message": "Retiré des favoris"}


def list_favorites(db: Session) -> list[str]:
    favorites = db.query(Favorite).all()
    return [f.product_name for f in favorites]


def list_history(db: Session) -> list[HistoryEntry]:
    return db.query(HistoryEntry).order_by(HistoryEntry.timestamp.desc()).all()


def add_from_favorites(db: Session) -> list[Product]:
    favorites = db.query(Favorite).all()
    if not favorites:
        raise HTTPException(status_code=400, detail="Aucun favori")

    existing_names = {p.name.lower() for p in db.query(Product).all()}
    added = []

    for fav in favorites:
        if fav.product_name.lower() not in existing_names:
            product = Product(name=fav.product_name, category="autre", quantity=1, bought=False)
            db.add(product)
            added.append(product)
            existing_names.add(fav.product_name.lower())

    db.commit()
    for p in added:
        db.refresh(p)
    return added
