from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from app.models.packages_model import Package
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.students_model import Student
from app.models.courses_model import Course
from app.models.package_courses import PackageCourse
from app.models.package_lectures import PackageLecture
from app.models.enrollments_model import Enrollment
from app.models.lecture_purchases import LecturePurchase
from app.models.lectures_model import Lecture
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
    courses = (db.query(Course, User)
                     .join(Teacher, Teacher.id == Course.teacher_id)
                     .join(User, User.id == Teacher.user_id)
                     .join(PackageCourse, PackageCourse.course_id == Course.id)
                     .filter(PackageCourse.package_id == package.id)
                     .all())

    package_courses = [
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
        for c, u in courses
    ]

    lectures = (db.query(Lecture, Course, User)
                .join(Course, Course.id == Lecture.course_id)
                .join(Teacher, Teacher.id == Course.teacher_id)
                .join(User, User.id == Teacher.user_id)
                .join(PackageLecture, PackageLecture.lecture_id == Lecture.id)
                .filter(PackageLecture.package_id == package.id))

    package_lectures = [
        {
            "id": l.id,
            "title": l.title,
            "price": l.price,
            "subject": c.subject,
            "stage": c.stage,
            "level": c.level,
            "cover_url": generate_url(c.cover_public_id),
            "teacher_first_name": u.first_name,
            "teacher_last_name": u.last_name,
            "pfp_url": generate_url(u.pfp_public_id)
        }
        for l, c, u in lectures
    ]

    return templates.TemplateResponse("package.html", {"request": request,
                                                       "package": {"id": package.id, "title": package.title, "price": float(package.price)},
                                                       "courses": package_courses,
                                                       "lectures": package_lectures})

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

    package_courses = db.query(Course).join(PackageCourse, PackageCourse.course_id == Course.id).filter(PackageCourse.package_id == id).all()
    package_lectures = db.query(Lecture).join(PackageLecture, PackageLecture.lecture_id == Lecture.id).filter(PackageLecture. package_id == id).all()
    if len(package_courses) == 0 and len(package_lectures) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        for course in package_courses:
            enrollment = Enrollment(
                student_id=student.id,
                course_id=course.id
            )
            db.add(enrollment)

        for lecture in package_lectures:
            lecture_purchase = LecturePurchase(
                student_id=student.id,
                lecture_id=lecture.id
            )
            db.add(lecture_purchase)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}