from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.students_model import Student
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.core.auth import validate_user
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

    try:
        user_id, user_role = validate_user(request.cookies.get("access_token"))
        user_student = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
        if not user_student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        user, student = user_student
        enrolled_courses = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
        enrolled_courses_ids = [row.course_id for row in enrolled_courses]
        enrolled = True if id in enrolled_courses_ids else False
    except HTTPException:
        enrolled = False

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
        "student_count": student_count,
        "enrolled": enrolled
    }

    return templates.TemplateResponse("course.html", {"request": request, "course": course_info})

