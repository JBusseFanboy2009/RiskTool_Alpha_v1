from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Portfolio, User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 1. User erstellen und direkt committen
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit() # Erst fest in die DB schreiben!
    db.refresh(user) # Lädt die ID des frisch erstellten Users

    # 2. Portfolio für diesen User erstellen
    main_portfolio = Portfolio(user_id=user.id, name="Main Portfolio")
    db.add(main_portfolio)
    db.commit()

    return user


#@router.post("/register", response_model=UserOut)
#def register_user(payload: UserCreate, db: Session = Depends(get_db)):
#    if db.query(User).filter(User.email == payload.email).first():
#        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
#
#    user = User(email=payload.email, hashed_password=hash_password(payload.password))
#    db.add(user)
#    db.flush()
#    db.add(Portfolio(user_id=user.id, name="Main Portfolio"))
#    db.commit()
#    db.refresh(user)
#    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong credentials")

    token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
