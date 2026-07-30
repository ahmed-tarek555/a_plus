from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.students_model import Student
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.models.exams_model import Exam
from app.models.homeworks_model import Homework
from app.models.submitted_homeworks import SubmittedHomework
from app.models.submittted_exams import SubmittedExam
from app.core.auth import validate_user
from app.database import get_db
from app.schemas.courses import AddCourse
from app.utils import generate_url
from app.config import BASE_DIR
from zoneinfo import ZoneInfo

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

@router.get("/submitted_homeworks/{id}")
def get_submitted_hms(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    homework = db.query(Homework).filter(Homework.id == id).first()
    if not homework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    submitted_hms = db.query(SubmittedHomework).filter(SubmittedHomework.homework_id == id).all()
    student_ids = [row.student_id for row in submitted_hms]
    results = db.query(User, Student).join(Student, Student.user_id == User.id).filter(Student.id.in_(student_ids)).all()
    student_lookup = {
        student.id: {
            "first_name": row.first_name,
            "last_name": row.last_name,
            "phone_number": row.phone_number,
            "parent_name": row.parent_name,
            "parent_phone_number": row.parent_phone_number,
        }
        for row, student in results
    }
    submittions = [
        {
            "id": hm.id,
            "url": generate_url(hm.public_id),
            "student": student_lookup[hm.student_id],
        }
        for hm in submitted_hms
    ]
    rest_students = (
        db.query(User)
        .join(Student, Student.user_id == User.id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id == homework.course_id, Student.id.notin_(student_ids))
        .all()
    )
    late_students = [
        {
            "first_name": student.first_name,
            "last_name": student.last_name,
            "phone_number": student.phone_number,
            "parent_name": student.parent_name,
            "parent_phone_number": student.parent_phone_number,
        }
        for student in rest_students
    ]
    return templates.TemplateResponse(
        "submittions.html",
        {
            "request": request,
            "submittions": submittions,
            "late_students": late_students,
            "submission_type": "homework",
            "item_title": homework.title,
        },
    )

@router.get("/submitted_exams/{id}")
def get_submitted_exams(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    exam = db.query(Exam).filter(Exam.id == id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    submitted_exams = db.query(SubmittedExam).filter(SubmittedExam.exam_id == id).all()
    student_ids = [row.student_id for row in submitted_exams]
    results = db.query(User, Student).join(Student, Student.user_id == User.id).filter(Student.id.in_(student_ids)).all()
    student_lookup = {
        student.id: {
            "first_name": row.first_name,
            "last_name": row.last_name,
            "phone_number": row.phone_number,
            "parent_name": row.parent_name,
            "parent_phone_number": row.parent_phone_number,
        }
        for row, student in results
    }
    submittions = [
        {
            "id": exam_submission.id,
            "mark": exam_submission.mark,
            "student": student_lookup[exam_submission.student_id],
        }
        for exam_submission in submitted_exams
    ]
    rest_students = (
        db.query(User)
        .join(Student, Student.user_id == User.id)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id == exam.course_id, Student.id.notin_(student_ids))
        .all()
    )
    late_students = [
        {
            "first_name": student.first_name,
            "last_name": student.last_name,
            "phone_number": student.phone_number,
            "parent_name": student.parent_name,
            "parent_phone_number": student.parent_phone_number,
        }
        for student in rest_students
    ]
    return templates.TemplateResponse(
        "submittions.html",
        {
            "request": request,
            "submittions": submittions,
            "late_students": late_students,
            "submission_type": "exam",
            "item_title": exam.title,
        },
    )

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
def add_course(request: Request, id: int, db: Session = Depends(get_db)):
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


