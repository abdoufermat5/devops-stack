import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://shopping:shopping@localhost:5432/shopping_db")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,       # connexions permanentes maintenues ouvertes
    max_overflow=10,    # connexions bonus temporaires en pic de charge
    pool_timeout=30,    # secondes max d'attente pour obtenir une connexion
    pool_pre_ping=True, # vérifie que la connexion est vivante avant de l'utiliser
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
