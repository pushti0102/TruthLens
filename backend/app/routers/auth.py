from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import UserRegister, UserLogin, Token, UserOut
from backend.app.security.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Check if email is already registered
    existing = db.query(User).filter(User.email == user_data.email.lower().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    if len(user_data.password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    # Hash password using Argon2id
    hashed = hash_password(user_data.password)

    new_user = User(
        email=user_data.email.lower().strip(),
        hashed_password=hashed,
        full_name=user_data.full_name,
        role=UserRole.USER,  # Default public role, cannot self-assign ADMIN
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log
    AuditService.log_event(
        db,
        event_type="REGISTER",
        action="User registration",
        user_id=new_user.id,
        user_email=new_user.email,
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
    )

    access_token = create_access_token(data={"sub": str(new_user.id), "role": new_user.role.value})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=new_user.role.value,
        email=new_user.email,
        full_name=new_user.full_name,
    )


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email.lower().strip()).first()
    client_ip = request.client.host if request.client else None

    if not user or not verify_password(login_data.password, user.hashed_password):
        AuditService.log_event(
            db,
            event_type="AUTH_FAILURE",
            action="Failed login attempt",
            user_email=login_data.email.lower().strip(),
            ip_address=client_ip,
            status="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    AuditService.log_event(
        db,
        event_type="LOGIN",
        action="User logged in",
        user_id=user.id,
        user_email=user.email,
        ip_address=client_ip,
        status="SUCCESS",
    )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role.value,
        email=user.email,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

