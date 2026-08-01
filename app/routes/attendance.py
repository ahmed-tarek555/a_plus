from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.models.attendance_model import Attendance
from app.models.enrollments_model import Enrollment
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.students_model import Student
from app.models.lectures_model import Lecture
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/attendance")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{lecture_id}")
def course_data(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, teacher = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    enrolled_students = (db.query(User, Attendance).join(Student, Student.user_id == User.id)
                         .join(Enrollment, Enrollment.student_id == Student.id)
                         .join(Course, Course.id == Enrollment.course_id)
                         .join(Lecture, Lecture.course_id == Course.id)
                         .outerjoin(Attendance, and_(Attendance.student_id == Student.id, Attendance.lecture_id == lecture_id))
                         .filter(Lecture.id == lecture_id)
                         .all())

    attended = []
    not_attended = []
    for student, attendance in enrolled_students:
        if attendance is not None:
            attended.append({
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "parent_name": student.parent_name,
                "parent_phone": student.parent_phone_number
            })
        else:
            not_attended.append({
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "parent_name": student.parent_name,
                "parent_phone": student.parent_phone_number
            })

    return templates.TemplateResponse("attendance.html", {"request": request, "attended": attended, "not_attended": not_attended})