from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.students_model import Student
from app.models.courses_model import Course
from app.models.teachers_model import Teacher
from app.models.packages_model import Package
from app.models.permissions_model import Permission
from app.models.package_courses import PackageCourse
from app.models.package_lectures import PackageLecture
from app.models.lectures_model import Lecture
from app.schemas.package import PackageCreate
from app.schemas.students import SearchStudents, EditLevel
from app.schemas.user import EditUser
from app.core.auth import validate_user
from app.core.security import hash_password
from app.database import get_db
from app.config import BASE_DIR
from zoneinfo import ZoneInfo

from app.utils import generate_url

router = APIRouter(prefix="/mod")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def login_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return templates.TemplateResponse("admin.html", {"request": request, "role": user_role})

@router.get("/pending_students")
def get_pending_students(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_approval").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    results = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.role == "student", User.is_active == False).all()

    return [
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone_number": user.phone_number,
            "parent_name": user.parent_name,
            "parent_phone_number": user.parent_phone_number,
            "date_joined": user.date_joined.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
            "level": student.level,
            "stage": student.stage
        }
        for user, student in results
    ]

@router.get("/pending_teachers")
def get_pending_teachers(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_approval").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    users = db.query(User).filter(User.role == "teacher", User.is_active == False).all()


    return [
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone_number": user.phone_number,
            "date_joined": user.date_joined.astimezone(ZoneInfo("Africa/Cairo")).strftime("%B %d, %Y"),
        }
        for user in users
    ]

@router.post("/approve/{id}")
def approve_user(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_approval").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_approved = db.query(User).filter(User.id == id).first()
    if not to_be_approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.execute(update(User).where(User.id == id).values(is_active=True))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"success": True}

@router.get("/get_teachers")
def get_teachers(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_teachers").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    teachers = db.query(User).filter(User.role == "teacher", User.is_active == True).all()

    return [
        {
            "id": t.id,
            "first_name": t.first_name,
            "last_name": t.last_name,
            "phone_number": t.phone_number,
            "date_joined": t.date_joined.strftime("%b %-d, %Y, %I:%M %p"),
            "pfp_url": generate_url(t.pfp_public_id)
        }
        for t in teachers
    ]


@router.post("/get_students")
def search_students(request: Request, payload: SearchStudents, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_students").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if payload.stage is not None and payload.level is None:
        query = db.query(User, Student).join(Student, Student.user_id == User.id).filter(Student.stage == payload.stage, User.is_active.is_(True))
    elif payload.level is not None and payload.stage is None:
        query = db.query(User, Student).join(Student, Student.user_id == User.id).filter(Student.level == payload.level, User.is_active.is_(True))
    elif payload.level is not None and payload.stage is not None:
        query = db.query(User, Student).join(Student, Student.user_id == User.id).filter(Student.stage == payload.stage, Student.level == payload.level, User.is_active.is_(True))
    else:
        query = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.is_active.is_(True))

    results = query.all()

    return [
        {
            "student_id": s.id,
            "stage": s.stage,
            "level": s.level,
            "user_id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "phone_number": u.phone_number,
            "parent_name": u.parent_name,
            "parent_phone_number": u.parent_phone_number
        }
        for u, s in results
    ]

@router.patch("/edit_level")
def edit_level(request: Request, payload: EditLevel, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_levels").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    stages = ("الثانوية", "الاعدادية", "الابتدائية")

    if payload.old_stage not in stages or payload.new_stage not in stages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stage")

    if payload.new_level > 3 and payload.new_stage != "الابتدائية":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid level")

    try:
        db.execute(update(Student).where(Student.stage==payload.old_stage, Student.level==payload.old_level).values(stage=payload.new_stage, level=payload.new_level))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/edit_user/{id}")
def edit_user(request: Request, id: int, payload: EditUser, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "user_editing").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_edited = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if to_be_edited.role == "student":
        student = db.query(Student).filter(Student.user_id == to_be_edited.id).first()
        if payload.level is not None:
            student.level = payload.level
        if payload.stage is not None:
            if payload.stage not in ("الثانوية", "الاعدادية", "الابتدائية"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
            else:
                student.stage = payload.stage

    if to_be_edited.role != "student" and payload.parent_name is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    if to_be_edited.role != "student" and payload.parent_phone_number is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    if payload.first_name is not None:
        to_be_edited.first_name = payload.first_name
    if payload.last_name is not None:
        to_be_edited.last_name = payload.last_name
    if payload.phone_number is not None:
        to_be_edited.phone_number = payload.phone_number
    if payload.username is not None:
        to_be_edited.username = payload.username
    if payload.password is not None:
        to_be_edited.password = hash_password(payload.password)
    if payload.parent_name is not None:
        to_be_edited.parent_name = payload.parent_name
    if payload.parent_phone_number is not None:
        to_be_edited.parent_phone_number = payload.parent_phone_number

    try:
        db.commit()
        db.refresh(to_be_edited)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/get_courses")
def get_courses(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_courses").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    results = db.query(Course, User).join(Teacher, Teacher.id == Course.teacher_id).join(User, User.id == Teacher.user_id).all()

    return [
        {
            "id": course.id,
            "price": course.price,
            "stage": course.stage,
            "level": course.level,
            "subject": course.subject,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "phone_number": teacher.phone_number,
            "pfp_url": generate_url(teacher.pfp_public_id)
        }
        for course, teacher in results
    ]

@router.get("/course_details/{course_id}")
def create_booking(request: Request, course_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_courses").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    course_info = {
        "id": course.id,
        "stage": course.stage,
        "price": course.price,
        "level": course.level,
        "subject": course.subject,
    }
    lectures = db.query(Lecture).filter(Lecture.course_id == course_id).all()

    course_lectures = [
        {
            "id": l.id,
            "title": l.title,
            "price": l.price,
        }
        for l in lectures
    ]
    return templates.TemplateResponse("course_details.html", {"request": request, "course_info": course_info, "lectures": course_lectures})

@router.get("/course_lectures/{course_id}")
def get_course_lectures(request: Request, course_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_courses").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    lectures = db.query(Lecture).join(Course, Lecture.course_id == Course.id).filter(Course.id == course_id).all()

    return [
        {
            "id": l.id,
            "title": l.title,
            "price": l.price
        }
        for l in lectures
    ]

@router.post("/create_package")
def create_package(request: Request, payload: PackageCreate, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_packages").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        package = Package(
            title=payload.title,
            price=payload.price
        )
        db.add(package)
        db.flush()

        for item in payload.courses_ids:
            package_course = PackageCourse(
                course_id=item.item_id,
                package_id=package.id
            )
            db.add(package_course)

        for item in payload.lectures_ids:
            package_lecture = PackageLecture(
                lecture_id=item.item_id,
                package_id=package.id
            )
            db.add(package_lecture)

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/delete_user/{id}")
def delete_user(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "user_deletion").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    to_be_deleted = db.query(User).filter(User.id == id).first()
    if not to_be_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(to_be_deleted)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/get_packages")
def get_packages(request: Request, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_packages").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    packages = db.query(Package).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "price": p.price
        }
        for p in packages
    ]

@router.delete("/delete_package/{id}")
def delete_package(request: Request, id: int, db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user.role != "mod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    permission = db.query(Permission).filter(Permission.user_id == user_id, Permission.type == "manage_packages").first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    package = db.query(Package).filter(Package.id == id).first()
    if not package:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(package)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}