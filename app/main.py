import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from routers.items import router
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shopping List API")
app.include_router(router)

# Expose /metrics pour Prometheus
# Doit être appelé APRÈS que tous les routers sont enregistrés
Instrumentator().instrument(app).expose(app)

@app.get("/")
def root():
    return {"message": "Shopping List API", "docs": "/docs"}
# retry
