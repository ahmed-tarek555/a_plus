from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import engine, Base, get_db
from app.models.users_model import User
from app.models.students_model import Student
from app.models.teachers_model import Teacher
from app.core.security import hash_password
from app.core.auth import validate_user
from app.config import BASE_DIR
from app.routes import home, login, signup, admin, profile, teachers, students, teacher_profile, course, manage_course, exams, course_material
from datetime import datetime, timezone

load_dotenv()

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI()

app.mount("/static",StaticFiles(directory=BASE_DIR / "static"), name="static")

# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home.router)
app.include_router(login.router)
app.include_router(signup.router)
app.include_router(admin.router)
app.include_router(profile.router)
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(teacher_profile.router)
app.include_router(course.router)
app.include_router(manage_course.router)
app.include_router(exams.router)
app.include_router(course_material.router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        user_id, user_role = validate_user(token)
        role = user_role
        is_logged = True
    except HTTPException:
        role = None
        is_logged = False

    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        new_admin = User(
            first_name="Admin",
            last_name="Admin",
            username="admin",
            phone_number="010",
            password=hash_password("123"),
            role="admin",
            date_joined=datetime.now(timezone.utc),
            is_active=True
        )
        db.add(new_admin)
        new_student = User(
            first_name="student",
            last_name="student",
            username="student",
            phone_number="011",
            password=hash_password("123"),
            role="student",
            parent_name="Tarek",
            parent_phone_number="01234",
            date_joined=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(new_student)
        db.flush()
        student = Student(
            user_id=new_student.id,
            level=3,
            stage="الثانوية"
        )
        db.add(student)
        new_teacher = User(
            first_name="teacher",
            last_name="teacher",
            username="teacher",
            phone_number="011231",
            password=hash_password("123"),
            role="teacher",
            date_joined=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(new_teacher)
        db.flush()
        teacher = Teacher(
            user_id = new_teacher.id
        )
        db.add(teacher)
        db.commit()

    return templates.TemplateResponse("home.html", {"request": request, "is_logged": is_logged, "role": role})