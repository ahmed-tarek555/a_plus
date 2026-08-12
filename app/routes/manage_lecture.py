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

router = APIRouter(prefix="/manage_lecture")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/{lecture_id}")
def course_data(request: Request, lecture_id: int, db: Session = Depends(get_db)):
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

    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    lecture_info = {
        "id": lecture.id,
        "title": lecture.title,
        "price": lecture.price,
        "video_id": lecture.video_id,
        "material_url": generate_url(lecture.material_public_id) if lecture.material_public_id is not None else None
    }

    return templates.TemplateResponse("manage_lecture.html", {"request": request, "lecture": lecture_info})


@router.post("/add_exam/{lecture_id}")
def add_exam(request: Request, payload: ExamCreate, lecture_id: int, db: Session = Depends(get_db)):
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
    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    exam = Exam(
        lecture_id=lecture_id,
        title=payload.title,
        start_time=payload.start_time,
        end_time= payload.start_time + timedelta(hours=payload.time),
    )
    db.add(exam)
    db.flush()

    for q in payload.questions:
        question = Question(
            exam_id=exam.id,
            is_choices=q.is_choices,
            head=q.head,
            correct_choice=q.correct_choice,
            model_answer=q.model_answer,
            answer_embedding=get_embedding(q.model_answer) if q.model_answer is not None else None,
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

@router.post("/add_homework/{lecture_id}")
def add_homework(request: Request, lecture_id: int, title: str = Form(...), due_date: Optional[datetime] = Form(...), homework: UploadFile = File(...), db: Session = Depends(get_db)):
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
    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not is_valid_image(homework):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    public_id = upload_file(homework)

    new_homework = Homework(
        lecture_id=lecture_id,
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

@router.get("/homeworks/{lecture_id}")
def get_homeworks(request: Request, lecture_id: int, db: Session = Depends(get_db)):
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
    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    homeworks = db.query(Homework).filter(Homework.lecture_id == lecture.id).all()
    return [
        {
            "id": homework.id,
            "title": homework.title,
            "url": generate_url(homework.public_id)
        }
        for homework in homeworks
    ]


@router.get("/exams/{lecture_id}")
def get_exams(request: Request, lecture_id: int, db: Session = Depends(get_db)):
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
    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    exams = db.query(Exam).filter(Exam.lecture_id == lecture.id).all()
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "start_time": exam.start_time,
            "end_time": exam.end_time
        }
        for exam in exams
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

    # rest_students = (
    #     db.query(User)
    #     .join(Student, Student.user_id == User.id)
    #     .join(Enrollment, Enrollment.student_id == Student.id)
    #     .filter(Enrollment.course_id == homework.course_id, Student.id.notin_(student_ids))
    #     .all()
    # )
    # late_students = [
    #     {
    #         "first_name": student.first_name,
    #         "last_name": student.last_name,
    #         "phone_number": student.phone_number,
    #         "parent_name": student.parent_name,
    #         "parent_phone_number": student.parent_phone_number,
    #     }
    #     for student in rest_students
    # ]
    return templates.TemplateResponse(
        "submittions.html",
        {
            "request": request,
            "submittions": submittions,
            "late_students": [],
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
    # rest_students = (
    #     db.query(User)
    #     .join(Student, Student.user_id == User.id)
    #     .join(Enrollment, Enrollment.student_id == Student.id)
    #     .filter(Enrollment.course_id == exam.course_id, Student.id.notin_(student_ids))
    #     .all()
    # )
    # late_students = [
    #     {
    #         "first_name": student.first_name,
    #         "last_name": student.last_name,
    #         "phone_number": student.phone_number,
    #         "parent_name": student.parent_name,
    #         "parent_phone_number": student.parent_phone_number,
    #     }
    #     for student in rest_students
    # ]
    return templates.TemplateResponse(
        "submittions.html",
        {
            "request": request,
            "submittions": submittions,
            "late_students": [],
            "submission_type": "exam",
            "item_title": exam.title,
        },
    )

@router.post("/upload_material/{lecture_id}")
def add_material(request: Request, lecture_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, teacher = result
    lecture = db.query(Lecture).join(Course, Course.id == Lecture.course_id).filter(Lecture.id == lecture_id, Course.teacher_id == teacher.id).first()

    public_id = upload_material(file)
    try:
        lecture.material_public_id = public_id
        db.commit()
        db.refresh(lecture)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}