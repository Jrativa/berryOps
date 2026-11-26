# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.backend.src.core.databases import init_db
from apps.backend.src.features.auth.presentation.routes import router as auth_router
from apps.backend.src.features.inventory.presentation.routes import router as inventory_router

init_db()
app = FastAPI(title="API Arándanos Fam", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(inventory_router, prefix="/inventory", tags=["inventory"])

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API del Cultivo de Arándanos"}