from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.students_model import Student
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.database import get_db
from app.config import BASE_DIR
from app.core.auth import validate_user
from datetime import datetime, timezone

router = APIRouter(prefix="/course_material")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def course_data(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result

    enrollment = db.query(Enrollment).filter(Enrollment.course_id == id, Enrollment.student_id == student.id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    material = "material to be constructed"
    return templates.TemplateResponse("course_material.html", {"request": request, "material": material})