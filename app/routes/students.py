from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from app.models.homeworks_model import Homework
from app.models.lectures_model import Lecture
from app.models.questions_model import Question
from app.models.submitted_homeworks import SubmittedHomework
from app.models.submittted_exams import SubmittedExam
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.models.students_model import Student
from app.models.courses_model import Course
from app.models.enrollments_model import Enrollment
from app.models.attendance_model import Attendance
from app.models.exams_model import Exam
from app.core.auth import validate_user
from app.database import get_db
from app.schemas.exam import ExamSubmit
from app.config import BASE_DIR
from datetime import datetime, timezone
from app.services.embedder import get_embedding, cosine_similarity
from app.utils import generate_url, is_valid_image, upload_file

router = APIRouter(prefix="/student")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.post("/enroll/{id}")
def enroll_course(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    course = db.query(Course).filter(Course.id == id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course does not exist")
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.course_id == id).first()
    if enrollment is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    enrollment = Enrollment(
        student_id=student.id,
        course_id=id
    )
    try:
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/unenroll/{id}")
def unenroll_course(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result

    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.course_id == id).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        db.delete(enrollment)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/my_courses")
def get_courses(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result

    courses = db.query(Course).join(Enrollment, Enrollment.course_id == Course.id).filter(Enrollment.student_id == student.id).all()

    student_courses = [
        {
            "id": course.id,
            "stage": course.stage,
            "level": course.level,
            "subject": course.subject,
        }
        for course in courses
    ]

    return templates.TemplateResponse("my_courses.html", {"request": request, "courses": student_courses})

@router.get("/exams")
def get_exams(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    exams = (
        db.query(Exam, Course, SubmittedExam)
              .join(Course, Course.id == Exam.course_id)
              .outerjoin(
                SubmittedExam,
                and_(
                    SubmittedExam.exam_id == Exam.id,
                    SubmittedExam.student_id == student.id
                    )
              )
              .join(Enrollment, Enrollment.course_id == Course.id)
              .filter(Enrollment.student_id == student.id)
              .all()
              )

    return [
        {
            "id": exam.id,
            "title": exam.title,
            "mark": submitted.mark if submitted is not None else None,
            "course": course.subject,
            "start_time": exam.start_time,
            "end_time": exam.end_time
        }
        for exam, course, submitted in exams
    ]

@router.post("/submit_homework/{id}")
def submit_homework(request: Request, id: int, hm: UploadFile = File(...), db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    homework = db.query(Homework).join(Course, Course.id == Homework.course_id).join(Enrollment, Enrollment.course_id == Course.id).filter(Homework.id == id, Enrollment.student_id == student.id).first()
    if not homework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if homework.due_date < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not is_valid_image(hm):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    public_id = upload_file(hm)

    new_submitted_hm = SubmittedHomework(
        homework_id = id,
        student_id = student.id,
        public_id = public_id
    )
    db.add(new_submitted_hm)

    try:
        db.commit()
        db.refresh(new_submitted_hm)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Homework is already submitted")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.post("/submit_exam/{id}")
def submit_exam(request: Request, id: int, payload: ExamSubmit, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account isn't active")
    exam = db.query(Exam).filter(Exam.id == id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    now = datetime.now(timezone.utc)
    if exam.start_time > now or exam.end_time < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not currently active")

    answers_data = []
    submitted_questions_ids = [row.question_id for row in payload.answers]
    questions = db.query(Question).filter(Question.id.in_(submitted_questions_ids)).all()
    answers = {row.question_id: row.answer for row in payload.answers}
    total_mark = 0
    for question in questions:
        if question.is_choices:
            if answers[question.id] == question.correct_choice:
                total_mark += question.mark
                answers_data.append({"question_id": question.id, "mark": question.mark})
        else:
            mark = int(round(question.mark * cosine_similarity(get_embedding(answers[question.id]), question.answer_embedding)))
            total_mark += mark
            answers_data.append({"question_id": question.id, "mark": mark})

    new_submitted_exam = SubmittedExam(
        exam_id=id,
        student_id=student.id,
        mark=total_mark
    )
    db.add(new_submitted_exam)
    try:
        db.commit()
        db.refresh(new_submitted_exam)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam already submitted")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return answers_data

@router.get("/materials/{id}")
def get_materials(request: Request, id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    teacher = db.query(User).join(Teacher, Teacher.user_id == User.id).join(Course, Course.teacher_id == Teacher.id).filter(Course.id == id).first()
    lectures = db.query(Lecture).filter(Lecture.course_id == id).all()
    homeworks = db.query(Homework).filter(Homework.course_id == id).all()

    teacher_info = {
        "id": teacher.id,
        "first_name": teacher.first_name,
        "last_name": teacher.last_name,
        "phone_number": teacher.phone_number,
        "pfp_url": generate_url(teacher.pfp_public_id)
    }
    course_lectures = [
        {
            "id": lec.id,
            "title": lec.title,
            "url": lec.url
        }
        for lec in lectures
    ]
    submitted_hms = db.query(SubmittedHomework).filter(SubmittedHomework.student_id == student.id).all()
    submitted_hms_ids = [row.homework_id for row in submitted_hms]

    course_homeworks = [
        {
            "id": hm.id,
            "title": hm.title,
            "due_date": hm.due_date.strftime("%b %-d, %Y, %I:%M %p"),
            "url": generate_url(hm.public_id),
            "submitted": True if hm.id in submitted_hms_ids else False
        }
        for hm in homeworks
    ]
    return templates.TemplateResponse("course_material.html", {"request": request, "teacher_info": teacher_info, "lectures": course_lectures, "homeworks": course_homeworks})

@router.post("/attend/{lecture_id}")
def attend(request: Request, lecture_id: int, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    attendance = db.query(Attendance).filter(Attendance.lecture_id == lecture_id, Attendance.student_id == student.id).first()
    if attendance is not None:
        return {"success": True}

    attendance = Attendance(
        student_id=student.id,
        lecture_id=lecture_id
    )
    db.add(attendance)
    try:
        db.commit()
        db.refresh(attendance)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}