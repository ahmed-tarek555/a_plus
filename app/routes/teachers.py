from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.models.packages_model import Package
from app.models.package_items import PackageItem
from app.core.auth import validate_user
from app.database import get_db
from app.schemas.courses import AddCourse
from app.schemas.package import PackageCreate
from app.config import BASE_DIR

router = APIRouter(prefix="/teacher")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def login_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return templates.TemplateResponse("teacher.html", {"request": request})

@router.get("/courses")
def get_courses(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    results = (
        db.query(Course, func.count(Enrollment.id).label("student_count"))
        .join(Teacher, Teacher.id == Course.teacher_id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .filter(Teacher.user_id == user_id)
        .group_by(Course.id)
        .all()
    )

    return [
        {
            "id": course.id,
            "price": course.price,
            "stage": course.stage,
            "level": course.level,
            "subject": course.subject,
            "is_public": course.is_public,
            "student_count": student_count
        }
        for course, student_count in results
    ]

@router.post("/add_course")
def add_course(request: Request, new_course: AddCourse, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user , teacher = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)

    if new_course.stage not in ("الثانوية", "الاعدادية", "الابتدائية"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stage")

    course = Course(
        teacher_id=teacher.id,
        price=new_course.price,
        stage=new_course.stage,
        level=new_course.level,
        subject=new_course.subject,
        is_public=True
    )
    try:
        db.add(course)
        db.commit()
        db.refresh(course)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.delete("/delete_course/{id}")
def delete_course(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user , teacher = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)

    course = db.query(Course).filter(Course.id == id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if course.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        db.delete(course)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/create_package")
def create_package(request: Request, payload: PackageCreate, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user , teacher = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE)
    try:
        package = Package(
            title=payload.title,
            price=payload.price,
        )
        db.add(package)
        db.flush()

        for item in payload.courses_ids:
            package_item = PackageItem(
                course_id=item.course_id,
                package_id=package.id
            )
            db.add(package_item)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}