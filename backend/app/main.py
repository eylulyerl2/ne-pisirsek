import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, families, invitations, meals, password_resets, plans, ratings, shopping, users

app = FastAPI(
    title="Ne Pisirsek? API",
    description="Kisisellestirmis haftalik yemek planlama sistemi",
    version="0.1.0"
)

# Yerelde her zaman localhost:3000'e izin verilir; üretimde ALLOWED_ORIGINS ortam değişkenine
# frontend'in gerçek adresi (virgülle ayrılmış, birden fazla olabilir) eklenir.
extra_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *extra_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(meals.router)
app.include_router(users.router)
app.include_router(ratings.router)
app.include_router(families.router)
app.include_router(invitations.router)
app.include_router(password_resets.router)
app.include_router(plans.router)
app.include_router(shopping.router)

@app.get("/")
def root():
    return {"message": "Ne Pisirsek? API calisiyor"}
