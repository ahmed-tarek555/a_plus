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

router = APIRouter(prefix="/course")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def course_data(request: Request, id: int, db: Session = Depends(get_db)):

    result = (
        db.query(Course, User, func.count(Enrollment.id).label("student_count"))
        .join(Teacher, Course.teacher_id == Teacher.id)
        .join(User, User.id == Teacher.user_id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .filter(Course.id == id)
        .group_by(Course.id, User.id)
        .first()
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist")

    course, user, student_count = result
    course_info = {
        "id": course.id,
        "subject": course.subject,
        "price": course.price,
        "stage": course.stage,
        "level": course.level,
        "teacher_first_name": user.first_name,
        "teacher_last_name": user.last_name,
        "teacher_pfp_url": generate_url(user.pfp_public_id),
        "student_count": student_count
    }

    return templates.TemplateResponse("course.html", {"request": request, "course": course_info})

