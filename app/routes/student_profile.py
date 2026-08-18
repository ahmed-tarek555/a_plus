from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.auth import validate_user
from app.models.attendance_model import Attendance
from app.models.lectures_model import Lecture
from app.models.students_model import Student
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/student_profile")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{student_id}")
def login_page(request: Request, student_id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role not in ("admin", "mod"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == student_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    s_user, student = result
    student_info = {
        "id": s_user.id,
        "first_name": s_user.first_name,
        "last_name": s_user.last_name,
        "phone_number": s_user.phone_number,
        "parent_name": s_user.parent_name,
        "parent_phone_number": s_user.parent_phone_number,
        "date_joined": s_user.date_joined,
        "stage": student.stage,
        "level": student.level
    }

    courses = (db.query(Course, User)
               .join(Teacher, Teacher.id == Course.teacher_id)
               .join(User, User.id == Teacher.user_id)
               .join(Enrollment, Enrollment.course_id == Course.id)
               .filter(Enrollment.student_id == student.id)
               .all())

    student_courses = [
        {
            "id": c.id,
            "subject": c.subject,
            "stage": c.stage,
            "level": c.level,
            "cover_url": generate_url(c.cover_public_id),
            "teacher_first_name": t.first_name,
            "teacher_last_name": t.last_name,
            "teacher_pfp_url": generate_url(t.pfp_public_id)
        }
        for c, t in courses
    ]

    attended_lectures = (db.query(Lecture, Course)
                         .join(Course, Course.id == Lecture.course_id)
                         .join(Attendance, Attendance.lecture_id == Lecture.id)
                         .filter(Attendance.student_id == student.id)
                         .all())

    student_lectures = [
        {
            "id": l.id,
            "title": l.title,
            "subject": c.subject,
            "stage": c.stage,
            "level": c.level,
            "cover_url": generate_url(c.cover_public_id)
        }
        for l, c in attended_lectures
    ]

    return templates.TemplateResponse("student_profile.html", {"request": request,
                                                               "student_info": student_info,
                                                               "student_courses": student_courses,
                                                               "attended_lectures": student_lectures})