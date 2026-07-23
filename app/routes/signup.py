from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.users_model import User
from app.models.students_model import Student
from app.models.teachers_model import Teacher
from app.core.security import hash_password
from app.core.auth import create_access_token
from app.database import get_db
from app.schemas.user import UserCreate
from app.config import BASE_DIR
from datetime import datetime, timezone

templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter(prefix="/signup")

@router.get("/")
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/get_signup")
async def signup(usercreate: UserCreate,
                db: Session = Depends(get_db)):

    user = db.query(User).filter(or_(User.email==usercreate.email, User.phone_number==usercreate.phone_number)).first()
    if user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or phone number already exists")

    if usercreate.role != "student" and usercreate.role != "teacher":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    if usercreate.role == "student" and usercreate.parent_name is None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)
    if usercreate.role == "student" and usercreate.parent_phone_number is None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)

    new_user = User(
        first_name=usercreate.first_name,
        last_name=usercreate.last_name,
        email=usercreate.email,
        phone_number=usercreate.phone_number,
        password=hash_password(usercreate.password),
        parent_name=usercreate.parent_name,
        parent_phone_number=usercreate.parent_phone_number,
        role=usercreate.role,
        date_joined=datetime.now(timezone.utc),
        is_active=False
    )
    db.add(new_user)
    db.flush()

    if usercreate.role == "student":
        new_student = Student(
            user_id=new_user.id,
            level=usercreate.level
        )
        db.add(new_student)

    elif usercreate.role == "teacher":
        new_teacher = Teacher(
            user_id=new_user.id,
            subject=usercreate.subject
        )
        db.add(new_teacher)

    try:

        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    token = create_access_token({
        "sub": str(new_user.id),
        "role": new_user.role
    })

    response = JSONResponse({"role": new_user.role})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    # for deployment
    # samesite = "none",
    # secure = True,

    return response
