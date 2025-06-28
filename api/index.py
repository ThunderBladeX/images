import os
import logging
import uuid
import secrets
import enum
from datetime import datetime, timedelta, timezone
from typing import Optional
import requests
from decouple import config, Csv
from alembic.config import Config
from alembic import command
from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, status, APIRouter
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from jose import JWTError, jwt
from mangum import Mangum
from passlib.context import CryptContext
from sqlalchemy import case
from sqlalchemy.orm import Session
from .models import (
    Base, SessionLocal, ImageRecord, ColorTag
)
from supabase import create_client, Client
from . import __init__

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPABASE_URL = config("SUPABASE_URL")
SUPABASE_KEY = config("SUPABASE_KEY")
SUPABASE_BUCKET = config("SUPABASE_BUCKET")
AUTH_USERNAME = config("AUTH_USERNAME")
AUTH_PASSWORD = config("AUTH_PASSWORD")
NEOCITIES_USERNAME = config("NEOCITIES_USERNAME")
NEOCITIES_API_KEY = config("NEOCITIES_API_KEY")
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
MIGRATION_SECRET = config("MIGRATION_SECRET", default=None)

app = FastAPI(
    title="Alathea's Art Manager",
    description="Personal Image Hosting and Neocities Gallery Updater"
)
api_router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

deployment_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(deployment_root, 'templates'))

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"Error initializing Supabase client: {e}")
    supabase = None

COLOR_ORDER = list(ColorTag)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username != AUTH_USERNAME:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

def upload_to_supabase(file_content: bytes, filename: str, content_type: str) -> str:
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        supabase.storage.from_(SUPABASE_BUCKET).upload(filename, file_content, {"content-type": content_type})
        return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
    except Exception as e:
        if 'Duplicate' in str(e):
            logger.warning(f"File {filename} already exists in Supabase. Re-using.")
            return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        logger.error(f"Failed to upload to Supabase: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload to Supabase: {str(e)}")

def update_neocities_gallery(db: Session):
    if not NEOCITIES_USERNAME or not NEOCITIES_API_KEY:
        logger.warning("Neocities credentials not set. Skipping update.")
        return "Neocities credentials not set. Skipped update."
    logger.info("Starting Neocities gallery update with custom sorting...")
    try:
        logger.info("Fetching images for Neocities gallery update with custom sorting...")
        color_order_case = case(
            {color.value: i for i, color in enumerate(COLOR_ORDER)},
            value=ImageRecord.color_tag
        )
        images = db.query(ImageRecord).order_by(ImageRecord.year_made.desc(), color_order_case).all()
        logger.info(f"Found {len(images)} images. Generating HTML...")

        template = templates.get_template("neocities_gallery_template.html")
        gallery_html = template.render({"images": images})
        logger.info("Uploading to Neocities...")
        response = requests.post(
            "https://neocities.org/api/upload",
            files={'gallery.html': gallery_html},
            headers={'Authorization': f'Bearer {NEOCITIES_API_KEY}'}
        )
        response.raise_for_status()
        return "Neocities gallery updated successfully."
    except Exception as e:
        error_text = getattr(e, 'response', {}).text if isinstance(e, requests.exceptions.RequestException) and getattr(e, 'response', None) is not None else str(e)
        logger.error(f"ERROR: Failed to update Neocities gallery: {error_text}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update Neocities: {error_text}")

@api_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "color_tags": [e.value for e in ColorTag]
    })

@api_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@api_router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_password = get_password_hash(config("AUTH_PASSWORD"))
    if not (secrets.compare_digest(form_data.username, AUTH_USERNAME) and verify_password(form_data.password, hashed_password)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/api/images")
async def get_images(db: Session = Depends(get_db), _=Depends(get_current_user)):
    images = db.query(ImageRecord).order_by(ImageRecord.uploaded_at.desc()).all()
    return images

@api_router.post("/api/upload")
async def upload_image(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
    file: UploadFile = File(...),
    title: str = Form(...),
    alt_text: Optional[str] = Form(None),
    color_tag: ColorTag = Form(...),
    year_made: int = Form(...),
    month_made: Optional[int] = Form(None),
    day_made: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    is_sensitive: bool = Form(False)
):
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    file_content = await file.read()
    original_ext = os.path.splitext(str(file.filename))[-1]
    uuid_filename = f"{uuid.uuid4()}{original_ext}"
    
    supabase_url = upload_to_supabase(file_content, uuid_filename, str(file.content_type))
    final_alt_text = alt_text if alt_text and alt_text.strip() else title
    markdown_url = f"![{final_alt_text}]({supabase_url})"
    
    new_image = ImageRecord(
        uuid_filename=uuid_filename,
        original_filename=str(file.filename),
        title=title,
        alt_text=final_alt_text,
        supabase_url=supabase_url,
        markdown_url=markdown_url,
        color_tag=color_tag,
        year_made=year_made,
        month_made=month_made,
        day_made=day_made,
        description=description,
        is_sensitive=is_sensitive,
    )
    db.add(new_image)
    db.commit()
    
    try:
        update_neocities_gallery(db)
        return {"message": "Image uploaded and gallery updated."}
    except HTTPException as e:
        logger.error(f"Neocities update failed after upload: {e.detail}")
        return JSONResponse(status_code=500, content={"message": "Image uploaded, but Neocities update failed.", "error": e.detail})

@api_router.delete("/api/delete/{image_id}", status_code=status.HTTP_200_OK)
async def delete_image(image_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if supabase:
        try:
            supabase.storage.from_(SUPABASE_BUCKET).remove([image.uuid_filename])
        except Exception as e:
            logger.warning(f"Could not delete {image.uuid_filename} from Supabase: {e}")
    
    db.delete(image)
    db.commit()
    
    try:
        update_neocities_gallery(db)
        return {"message": "Image deleted and Neocities updated."}
    except HTTPException as e:
        return JSONResponse(status_code=500, content={"message": "Image deleted, but Neocities update failed.", "error": e.detail})

@api_router.post("/api/update-gallery")
async def manual_gallery_update_endpoint(db: Session = Depends(get_db), _=Depends(get_current_user)):
    try:
        message = update_neocities_gallery(db)
        return {"message": message}
    except HTTPException as e:
        raise e

@api_router.get("/manage/migrations", response_class=HTMLResponse, include_in_schema=False)
async def migration_page():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>DB Migration</title></head>
    <body>
        <h1>Database Migration</h1>
        <form action="/run-migrations" method="post">
            <label for="secret">Migration Secret:</label>
            <input type="password" id="secret" name="secret" required>
            <button type="submit">Run Migrations</button>
        </form>
    </body>
    </html>
    """

@api_router.post("/run-migrations", include_in_schema=False)
async def run_migrations_endpoint(secret: str = Form(...)):
    if not MIGRATION_SECRET or secret != MIGRATION_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    deployment_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_cwd = os.getcwd()
    try:
        logger.info("Running migrations programmatically from endpoint...")
        logger.info(f"Original CWD: {original_cwd}")
        os.chdir(deployment_root)
        logger.info(f"Temporarily changed CWD to: {os.getcwd()}")
        
        alembic_ini_path = os.path.join(deployment_root, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")

        logger.info("Migrations completed successfully.")
        return HTMLResponse("<h1>Migrations ran successfully!</h1>")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(f"<h1>Migration Failed</h1><p>{str(e)}</p>", status_code=500)
    finally:
        os.chdir(original_cwd)
        logger.info(f"Restored CWD to: {original_cwd}")

app.include_router(api_router)
