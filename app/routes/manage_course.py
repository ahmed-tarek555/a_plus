from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.models.exams_model import Exam
from app.models.questions_model import Question
from app.models.choices_model import Choice
from app.models.homeworks_model import Homework
from app.schemas.exam import ExamCreate
from app.core.auth import validate_user
from app.database import get_db
from app.utils import is_valid_image, upload_file, generate_url
from app.config import BASE_DIR
from datetime import datetime, timezone

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

@router.post("/add_exam/{id}")
def add_exam(request: Request, payload: ExamCreate, id: int, db: Session = Depends(get_db)):
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

    exam = Exam(
        course_id=id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        created_at=datetime.now(timezone.utc)
    )
    db.add(exam)
    db.flush()

    for q in payload.questions:
        question = Question(
            exam_id=exam.id,
            is_choices=q.is_choices,
            head=q.head,
            correct_choice=q.correct_choice,
            mark=q.mark
        )
        db.add(question)
        db.flush()

        if q.is_choices:
            for c in q.choices:
                choice = Choice(question_id=question.id, text=c.text)
                db.add(choice)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    db.refresh(exam)
    return {"success": True}

@router.post("/add_homework/{id}")
def add_homework(request: Request, id: int, title: str, due_date: Optional[datetime] = None, homework: UploadFile = File(...), db: Session = Depends(get_db)):
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

    if not is_valid_image(homework):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    public_id = upload_file(homework)

    new_homework = Homework(
        course_id=id,
        title=title,
        due_date=due_date,
        public_id=public_id
    )
    db.add(new_homework)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    db.refresh(new_homework)
    return {"success": True}

@router.get("/homeworks/{id}")
def get_homeworks(request: Request, id: int, db: Session = Depends(get_db)):
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

    homeworks = db.query(Homework).filter(Homework.course_id == course.id).all()
    return [
        {
            "id": homework.id,
            "title": homework.title,
            "url": generate_url(homework.public_id)
        }
        for homework in homeworks
    ]


@router.get("/exams/{id}")
def get_exams(request: Request, id: int, db: Session = Depends(get_db)):
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

    exams = db.query(Exam).filter(Exam.course_id == course.id).all()
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "due_date": exam.due_date
        }
        for exam in exams
    ]