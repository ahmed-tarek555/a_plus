from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.questions_model import Question
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.exams_model import Exam
from app.models.choices_model import Choice
from app.models.enrollments_model import Enrollment
from app.utils import generate_url
from app.database import get_db
from app.config import BASE_DIR
from datetime import datetime, timezone
from collections import defaultdict

router = APIRouter(prefix="/exam")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{id}")
def course_data(request: Request, id: int, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    exam = db.query(Exam).filter(Exam.id == id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if exam.start_time > now or exam.end_time < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    questions = db.query(Question).filter(Question.exam_id == exam.id).all()
    question_ids = [q.id for q in questions]
    choices = db.query(Choice).filter(Choice.question_id.in_(question_ids)).all()
    choices_by_question = defaultdict(list)
    for c in choices:
        choices_by_question[c.question_id].append({"id": c.id, "text": c.text})

    student_exam = {
        "id": exam.id,
        "title": exam.title,
        "questions": [
            {
                "id": question.id,
                "is_choices": question.is_choices,
                "head": question.head,
                "choices": [choice for choice in choices_by_question[question.id]] if question.is_choices else None,
                "mark": question.mark
            }
            for question in questions
        ]
    }

    return templates.TemplateResponse("exam.html", {"request": request, "exam": student_exam})