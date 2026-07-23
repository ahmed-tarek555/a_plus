from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.auth import validate_user
from app.database import get_db
from app.config import BASE_DIR
from zoneinfo import ZoneInfo

templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter(prefix="/home")
