import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.seed_data import seed_database
from app.api.v1 import catalogs, budgets, audit

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar tablas en base de datos
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed si la base de datos es nueva
    db = SessionLocal()
    try:
        from app.models.category import Category
        if db.query(Category).count() == 0:
            print("[INFO] Inicializando catálogo maestro y datos de presupuesto EDIMCA...")
            seed_database(db)
            print("[INFO] Catálogo y proyecciones inicializadas correctamente.")
    finally:
        db.close()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API REST para proyección y control del presupuesto anual con cálculo automático de totales y auditoría inmutable.",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de routers de API
app.include_router(catalogs.router, prefix=settings.API_V1_STR, tags=["Catálogos y Años"])
app.include_router(budgets.router, prefix=settings.API_V1_STR, tags=["Presupuesto y Proyecciones"])
app.include_router(audit.router, prefix=settings.API_V1_STR, tags=["Auditoría e Historial"])

# Servir archivos estáticos del frontend si existen
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": f"Bienvenido al {settings.PROJECT_NAME}. Documentación en /docs"}

@app.get("/health", tags=["Salud"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
