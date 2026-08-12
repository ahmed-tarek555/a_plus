from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.packages_model import Package
from app.models.submitted_homeworks import SubmittedHomework
from app.models.submittted_exams import SubmittedExam
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.students_model import Student
from app.models.lectures_model import Lecture
from app.models.homeworks_model import Homework
from app.models.exams_model import Exam
from app.models.lecture_purchases import LecturePurchase
from app.utils import generate_url
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/lecture")

templates = Jinja2Templates(directory=BASE_DIR / "templates")


@router.get("/{lecture_id}")
def course_data(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    lecture = (db.query(Lecture)
               .join(LecturePurchase, LecturePurchase.lecture_id == Lecture.id)
               .filter(LecturePurchase.lecture_id == lecture_id, LecturePurchase.student_id == student.id)
               .first())

    homeworks = (db.query(Homework, SubmittedHomework)
                 .outerjoin(SubmittedHomework, and_(SubmittedHomework.homework_id == Homework.id, SubmittedHomework.student_id == student.id))
                 .filter(Homework.lecture_id == lecture_id)
                 .all())

    exams = (db.query(Exam, SubmittedExam)
             .outerjoin(SubmittedExam, and_(SubmittedExam.exam_id == Exam.id, SubmittedExam.student_id == student.id))
             .filter(Exam.lecture_id == lecture_id)
             .all())

    material = {
        "id": lecture.id,
        "title": lecture.title,
        "video_id": lecture.video_id,
        "material_url": generate_url(lecture.material_public_id) if lecture.material_public_id is not None else None,
        "homeworks": [
            {
                "id": hm.id,
                "title": hm.title,
                "due_date": hm.due_date.strftime("%b %-d, %Y, %I:%M %p"),
                "url": generate_url(hm.public_id),
                "submitted": True if submittedhm is not None else False
            }
            for hm, submittedhm in homeworks
        ],
        "exams": [
            {
                "id": ex.id,
                "tite": ex.title,
                "start_time": ex.start_time.strftime("%b %-d, %Y, %I:%M %p"),
                "end_time": ex.end_time.strftime("%b %-d, %Y, %I:%M %p"),
                "mark": submittedex.mark if submittedex is not None else None
            }
            for ex, submittedex in exams
        ]
    }
    return templates.TemplateResponse("lecture.html", {"request": request, "material": material})