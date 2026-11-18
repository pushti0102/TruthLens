import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure root workspace is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.security.auth import hash_password
from backend.app.security.keys import crypto_manager
from backend.app.routers import auth, media, publishers, dashboard, admin, system

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="TruthLens — AI-Powered Digital Media Authenticity & Provenance Verification System (AI 331)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    # 1. Initialize DB tables
    Base.metadata.create_all(bind=engine)

    # 2. Seed development accounts if not present
    db = SessionLocal()
    try:
        # Admin account
        admin_user = db.query(User).filter(User.email == "admin@truthlens.local").first()
        if not admin_user:
            admin_user = User(
                email="admin@truthlens.local",
                hashed_password=hash_password("AdminPass123!"),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin_user)

        # Publisher account
        publisher_user = db.query(User).filter(User.email == "publisher@truthlens.local").first()
        if not publisher_user:
            publisher_user = User(
                email="publisher@truthlens.local",
                hashed_password=hash_password("PublisherPass123!"),
                full_name="Trusted Media Publisher",
                role=UserRole.PUBLISHER,
                is_active=True,
            )
            db.add(publisher_user)

        # Standard user account
        normal_user = db.query(User).filter(User.email == "user@truthlens.local").first()
        if not normal_user:
            normal_user = User(
                email="user@truthlens.local",
                hashed_password=hash_password("UserPass123!"),
                full_name="Standard Verifier",
                role=UserRole.USER,
                is_active=True,
            )
            db.add(normal_user)

        db.commit()
    finally:
        db.close()

    # 3. Initialize Cryptographic Keys & Registry
    _ = crypto_manager.get_private_key()
    print("[+] TruthLens Backend Initialized. Database, Auth, Cryptography & AI interfaces ready.")


# Include API Routers
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(media.router)
app.include_router(publishers.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to TruthLens API — Verify the media. Inspect the evidence.",
        "docs": "/docs",
        "health": "/api/health",
        "version": settings.PROJECT_VERSION,
    }

