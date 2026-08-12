from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.models.exams_model import Exam
from app.models.homeworks_model import Homework
from app.models.students_model import Student
from app.models.submitted_homeworks import SubmittedHomework
from app.models.submittted_exams import SubmittedExam
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.models.lectures_model import Lecture
from app.utils import generate_url
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/my_course")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{course_id}")
def course_data(request: Request, course_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    course_info = (db.query(Course, User)
              .join(Teacher, Teacher.id == Course.teacher_id)
              .join(User, User.id == Teacher.user_id)
              .join(Enrollment, Enrollment.course_id == Course.id)
              .filter(Enrollment.student_id == student.id, Course.id == course_id)
              .first())
    if not course_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    course, teacher = course_info
    lectures = db.query(Lecture).filter(Lecture.course_id == course.id).all()
    course_lectures = [
        {
            "id": lec.id,
            "title": lec.title,
        }
        for lec in lectures
    ]

    my_course = {
        "id": course.id,
        "subject": course.subject,
        "stage": course.stage,
        "level": course.level,
        "lectures": course_lectures,
        "teacher_first_name": teacher.first_name,
        "teacher_last_name": teacher.last_name,
        "teacher_pfp_url": generate_url(teacher.pfp_public_id),
    }

    return templates.TemplateResponse("course_material.html", {"request": request, "course": my_course})

@router.get("/lecture/{lecture_id}")
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
                .join(Course, Course.id == Lecture.course_id)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .filter(Lecture.id == lecture_id, Enrollment.student_id == student.id)
                .first())

    homeworks = (db.query(Homework, SubmittedHomework)
                 .outerjoin(SubmittedHomework, and_(SubmittedHomework.homework_id == Homework.id, SubmittedHomework.student_id == student.id))
                 .filter(Homework.lecture_id == lecture_id)
                 .all())

    exams = (db.query(Exam, SubmittedExam)
             .outerjoin(SubmittedExam, and_(SubmittedExam.exam_id == Exam.id, SubmittedExam.student_id == student.id))
             .filter(Exam.lecture_id == lecture_id)
             .all())

    return {
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