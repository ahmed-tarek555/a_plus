from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.models.teachers_model import Teacher
from app.core.auth import validate_user
from app.utils import generate_url, is_valid_image, delete_file, upload_pfp
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/profile")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def login_page(request: Request):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return templates.TemplateResponse("profile.html", {"request": request})

@router.get("/data")
def get_data(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    if user_role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    user = db.query(User).filter(User.id == user_id).first()
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "date_joined": user.date_joined,
        "is_active": user.is_active,
        "pfp_url": generate_url(user.pfp_public_id)
    }


@router.post("/upload_pfp")
def upload_picture(request: Request,
               pfp: UploadFile = File(...),
               db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    result = db.query(User, Teacher).join(Teacher, Teacher.user_id == User.id).filter(User.id == user_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user, teacher = result
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not is_valid_image(pfp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    public_id = upload_pfp(pfp)
    if user.pfp_public_id is not None:
        delete_file(user.pfp_public_id, "image")
    user.pfp_public_id = public_id
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return {"pfp_url": generate_url(public_id)}
