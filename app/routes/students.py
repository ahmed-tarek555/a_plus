from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from app.models.homeworks_model import Homework
from app.models.lecture_purchases import LecturePurchase
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
from app.models.private_lectures import PrivateLecture
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

@router.post("/buy_lecture/{lecture_id}")
def buy_lecture(request: Request, lecture_id: int, db: Session = Depends(get_db)):
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

    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        new_purchase = LecturePurchase(
            lecture_id=lecture_id,
            student_id=student.id
        )
        db.add(new_purchase)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

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
            "cover_url": generate_url(course.cover_public_id)
        }
        for course in courses
    ]

    return templates.TemplateResponse("my_courses.html", {"request": request, "courses": student_courses})

@router.get("/my_lectures")
def get_lectures(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, student = result

    lec_info = (db.query(Lecture, Course, User)
                .join(Course, Course.id == Lecture.course_id)
                .join(Teacher, Teacher.id == Course.teacher_id)
                .join(User, User.id == Teacher.user_id)
                .join(LecturePurchase, LecturePurchase.lecture_id == Lecture.id)
                .filter(LecturePurchase.student_id == student.id)
                .all())

    student_lectures = [
        {
            "id": lec.id,
            "title": lec.title,
            "subject": course.subject,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
            "pfp": generate_url(teacher.pfp_public_id) if teacher.pfp_public_id is not None else None,
            "cover_url": generate_url(course.cover_public_id)
        }
        for lec, course, teacher in lec_info
    ]
    return templates.TemplateResponse("my_lectures.html", {"request": request, "lectures": student_lectures})

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
    homework = db.query(Homework).filter(Homework.id == id).first()
    if not homework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if homework.due_date < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not is_valid_image(hm):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    public_id = upload_file(hm, "homeworks")

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
            similarity = cosine_similarity(get_embedding(answers[question.id]), question.answer_embedding)
            if similarity > 0.8:
                mark = question.mark
                total_mark += mark
            else:
                mark = int(round(question.mark * similarity))
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
    try:
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.patch("/book_private/{id}")
def book_private(request: Request, id: int, db: Session = Depends(get_db)):
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

    private_lecture = db.query(PrivateLecture).filter(PrivateLecture.id == id).with_for_update().first()
    if not private_lecture:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if private_lecture.student_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    try:
        private_lecture.student_id = student.id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}

@router.get("/private")
def book_private(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = db.query(User, Student).join(Student, Student.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return templates.TemplateResponse("my_private_lectures.html", {"request": request})


@router.get("/get_private_lectures")
def book_private(request: Request, db: Session = Depends(get_db)):
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

    lec_teacher = (db.query(PrivateLecture, User)
                   .join(Teacher, Teacher.id == PrivateLecture.teacher_id)
                   .join(User, User.id == Teacher.user_id)
                   .filter(PrivateLecture.student_id == student.id)
                   .all())

    return [
        {
            "id": lec.id,
            "title": lec.title,
            "subject": lec.subject,
            "start_date": lec.start_date.strftime("%b %-d, %Y, %I:%M %p"),
            "link": lec.link,
            "teacher_first_name": teacher.first_name,
            "teacher_last_name": teacher.last_name,
            "teacher_pfp_url": generate_url(teacher.pfp_public_id)
        }
        for lec, teacher in lec_teacher
    ]