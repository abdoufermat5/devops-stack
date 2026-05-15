import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from db import engine, Base
from models.item import Product, HistoryEntry, Favorite
from routers.items import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shopping List API")

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Shopping List API", "docs": "/docs"}
