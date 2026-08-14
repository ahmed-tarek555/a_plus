from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.courses_model import Course
from app.models.users_model import User
from app.models.enrollments_model import Enrollment
from app.models.teachers_model import Teacher
from app.models.packages_model import Package
from app.models.private_lectures import PrivateLecture
from app.utils import generate_url
from app.database import get_db
from app.config import BASE_DIR

templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter(prefix="/home")

@router.get("/courses")
def get_courses(request: Request, db: Session = Depends(get_db)):

    result = (
        db.query(Course, User, func.count(Enrollment.id).label("student_count"))
        .join(Teacher, Course.teacher_id == Teacher.id)
        .join(User, Teacher.user_id == User.id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .filter(Course.is_public == True)
        .group_by(Course.id, User.id)
        .all()
    )

    return [
        {
            "id": row.Course.id,
            "price": float(row.Course.price),
            "subject": row.Course.subject,
            "stage": row.Course.stage,
            "level": row.Course.level,
            "teacher_first_name": row.User.first_name,
            "teacher_last_name": row.User.last_name,
            "student_count": row.student_count,
            "cover_url": generate_url(row.Course.cover_public_id)
        }
        for row in result
    ]

@router.get("/private_lectures")
def get_private(request: Request, db: Session = Depends(get_db)):

    result = (db.query(PrivateLecture, User)
              .join(Teacher, Teacher.id == PrivateLecture.teacher_id)
              .join(User, User.id == Teacher.user_id)
              .filter(PrivateLecture.student_id.is_(None)).all())

    return[
        {
            "id": lec.id,
            "title": lec.title,
            "subject": lec.subject,
            "start_date": lec.start_date,
            "price": float(lec.price),
            "teacher_first_name": teacher.first_name,
            "teacher_last_name": teacher.last_name,
            "teacher_phone_number": teacher.phone_number,
            "teacher_pfp_url": generate_url(teacher.pfp_public_id)
        }
        for lec, teacher in result
    ]

@router.get("/packages")
def get_packages(request: Request, db: Session = Depends(get_db)):

    packages = db.query(Package).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "price": float(p.price)
        }
        for p in packages
    ]


@router.get("/teachers")
def get_teachers(request: Request, db: Session = Depends(get_db)):
    teachers = db.query(User).filter(User.role == "teacher", User.is_active == True).all()

    return [
        {
            "id": teacher.id,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "pfp_url": generate_url(teacher.pfp_public_id)
        }
        for teacher in teachers
    ]