from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from app.models.packages_model import Package
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.students_model import Student
from app.models.courses_model import Course
from app.models.package_items import PackageItem
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/package")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def course_data(request: Request, id: int, db: Session = Depends(get_db)):

    package = db.query(Package).filter(Package.id == id).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    resutl = (db.query(Course, User)
                     .join(Teacher, Teacher.id == Course.teacher_id)
                     .join(User, User.id == Teacher.user_id)
                     .join(PackageItem, PackageItem.course_id == Course.id)
                     .filter(PackageItem.package_id == package.id)
                     .all())

    courses = [
        {
            "id": c.id,
            "stage": c.stage,
            "level": c.level,
            "subject": c.subject,
            "price": float(c.price),
            "cover_url": generate_url(c.cover_public_id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "pfp_url": generate_url(u.pfp_public_id)
        }
        for c, u in resutl
    ]

    return templates.TemplateResponse("package.html", {"request": request, "package": {"id": package.id, "title": package.title, "price": float(package.price)}, "courses": courses})

@router.post("/buy/{id}")
def buy_package(request: Request, id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    package_items = db.query(Course).join(PackageItem, PackageItem.course_id == Course.id).filter(PackageItem.package_id == id).all()
    if len(package_items) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        for course in package_items:
            enrollment = Enrollment(
                student_id=student.id,
                course_id=course.id
            )
            db.add(enrollment)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}