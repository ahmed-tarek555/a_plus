from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.students_model import Student
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/admin")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def login_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/pending_students")
def get_pending_students(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    results = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.role == "student", User.is_active == False).all()

    return [
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone_number": user.phone_number,
            "parent_name": user.parent_name,
            "parent_phone_number": user.parent_phone_number,
            "date_joined": user.date_joined.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
            "level": student.level,
            "stage": student.stage
        }
        for user, student in results
    ]

@router.get("/pending_teachers")
def get_pending_teachers(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    users = db.query(User).filter(User.role == "teacher", User.is_active == False).all()


    return [
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone_number": user.phone_number,
            "date_joined": user.date_joined.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
        }
        for user in users
    ]

@router.post("/approve/{id}")
def approve_user(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    to_be_approved = db.query(User).filter(User.id == id).first()
    if not to_be_approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.execute(update(User).where(User.id == id).values(is_active=True))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}

@router.post("/delete_user/{id}")
def approve_user(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_deleted = db.query(User).filter(User.id == id).first()
    if not to_be_deleted:
        return {"success": True}
    try:
        db.delete(to_be_deleted)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}