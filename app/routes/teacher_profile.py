from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/teacher_profile")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def login_page(request: Request, id: int, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    teacher_data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "pfp_url": generate_url(user.pfp_public_id)
    }

    result = (
        db.query(Course, func.count(Enrollment.id).label("student_count"))
        .join(Teacher, Teacher.id == Course.teacher_id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .filter(Teacher.user_id == id, Course.is_public == True)
        .group_by(Course.id)
        .all()
    )

    teacher_courses = [
        {
            "id": course.id,
            "price": course.price,
            "stage": course.stage,
            "level": course.level,
            "subject": course.subject,
            "student_count": student_count
        }
        for course, student_count in result
    ]

    return templates.TemplateResponse("teacher_profile.html", {"request": request, "data": teacher_data, "courses": teacher_courses})

