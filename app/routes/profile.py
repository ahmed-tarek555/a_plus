from fastapi import APIRouter, Depends, status, HTTPException, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.users_model import User
from app.core.auth import validate_user
from app.core.security import hash_password
from app.schemas.user import EditProfile
from app.utils import generate_url, is_valid_image, delete_file, upload_image
from app.database import get_db
from app.config import BASE_DIR

router = APIRouter(prefix="/profile")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

@router.get("/")
def login_page(request: Request, db: Session = Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        user_id, user_role = validate_user(token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        data =  {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "phone_number": user.phone_number,
            "parent_name": user.parent_name,
            "parent_phone_number": user.parent_phone_number,
            "role": user.role,
            "date_joined": user.date_joined,
            "is_active": user.is_active,
            "pfp_url": generate_url(user.pfp_public_id)
        }
    except HTTPException:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("profile.html", {"request": request, "data": data})

@router.post("/upload_pfp")
def upload_picture(request: Request,
               pfp: UploadFile = File(...),
               db: Session = Depends(get_db)):

    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if not is_valid_image(pfp):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    public_id = upload_image(pfp, "teachers/pfp")
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

@router.patch("/edit")
def edit_info(request: Request, edit_profile: EditProfile, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    user_id, user_role = validate_user(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if edit_profile.password is not None:
        user.password = hash_password(edit_profile.password)

    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return {"success": True}