from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.enrollments_model import Enrollment
from app.models.submitted_homeworks import SubmittedHomework
from app.models.submittted_exams import SubmittedExam
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.exams_model import Exam
from app.models.questions_model import Question
from app.models.choices_model import Choice
from app.models.homeworks_model import Homework
from app.models.students_model import Student
from app.models.lectures_model import Lecture
from app.schemas.exam import ExamCreate
from app.schemas.courses import UploadLecture
from app.core.auth import validate_user
from app.services.embedder import get_embedding
from app.database import get_db
from app.utils import is_valid_image, upload_file, generate_url, upload_material, extract_youtube_id
from app.config import BASE_DIR
from datetime import datetime, timedelta

router = APIRouter(prefix="/manage_course")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def course_data(request: Request, id: int, db: Session = Depends(get_db)):
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
    course = db.query(Course).filter(Course.id == id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    course_info = {
        "id": course.id,
        "subject": course.subject,
        "level": course.level,
        "stage": course.stage
    }

    return templates.TemplateResponse("manage_course.html", {"request": request, "course_info": course_info})

@router.get("/lectures/{course_id}")
def get_lectures(request: Request, course_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    lectures = db.query(Lecture).filter(Lecture.course_id == course_id).all()

    return [
        {
            "id": lec.id,
            "title": lec.title,
        }
        for lec in lectures
    ]

@router.post("/upload_lecture/{course_id}")
def upload_material(request: Request, course_id: int, payload: UploadLecture, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, teacher = result

    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher.id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    lecture = Lecture(
        course_id=course.id,
        title=payload.title,
        price=payload.price,
        video_id=extract_youtube_id(payload.url)
    )
    db.add(lecture)

    try:
        db.commit()
        db.refresh(lecture)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}