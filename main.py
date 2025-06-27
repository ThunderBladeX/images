from fastapi import (
    FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, status
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, Enum
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from supabase import create_client, Client
import os
from datetime import datetime
from typing import Optional, List
import secrets
import requests
import uuid
import enum

# Load environment variables for Render deployment
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "images")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
NEOCITIES_USERNAME = os.getenv("NEOCITIES_USERNAME")
NEOCITIES_API_KEY = os.getenv("NEOCITIES_API_KEY")

# Basic validation for essential variables
if not all([DATABASE_URL, SUPABASE_URL, SUPABASE_KEY, AUTH_USERNAME, AUTH_PASSWORD]):
    raise Exception("Missing essential environment variables (DB, Supabase, Auth)")

app = FastAPI(title="Alathea's Art Manager", description="Personal Image Hosting and Neocities Gallery Updater")
security = HTTPBasic()
templates = Jinja2Templates(directory="templates")

# Database Setup (PostgreSQL with SQLAlchemy)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    supabase = None

# Define colors in a specific order for sorting
class ColorTag(str, enum.Enum):
    red = "red"
    orange = "orange"
    yellow = "yellow"
    green = "green"
    blue = "blue"
    indigo = "indigo"
    violet = "violet"
    black = "black"
    white = "white"

COLOR_ORDER = list(ColorTag)

class ImageRecord(Base):
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid_filename = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    supabase_url = Column(String, nullable=False)
    markdown_url = Column(Text, nullable=False)
    color_tag = Column(Enum(ColorTag), nullable=False)
    year_made = Column(Integer, index=True, nullable=False)
    is_sensitive = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    """Authenticates user against environment variables."""
    correct_username = secrets.compare_digest(credentials.username, AUTH_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, AUTH_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"}
        )
    return credentials.username

def upload_to_supabase(file_content: bytes, filename: str) -> str:
    """Uploads a file to Supabase Storage and returns the public URL."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    try:
        # Check if bucket exists
        buckets = supabase.storage.list_buckets()
        if not any(b.name == SUPABASE_BUCKET for b in buckets):
             supabase.storage.create_bucket(SUPABASE_BUCKET, public=True)
             print(f"Created Supabase bucket: {SUPABASE_BUCKET}")
        
        supabase.storage.from_(SUPABASE_BUCKET).upload(filename, file_content, {"content-type": "image/webp"})
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        return public_url
    except Exception as e:
        # Check if it's a duplicate file error, which we can ignore
        if 'Duplicate' in str(e):
            print(f"File {filename} already exists in Supabase. Re-using.")
            return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
        raise HTTPException(status_code=500, detail=f"Failed to upload to Supabase: {str(e)}")

def update_neocities_gallery(db: Session):
    """Generates and uploads the gallery.html file to Neocities."""
    if not NEOCITIES_USERNAME or not NEOCITIES_API_KEY:
        print("Neocities credentials not set. Skipping update.")
        return "Neocities credentials not set. Skipped update."

    print("Fetching images for Neocities gallery update...")
    # Custom sorting: first by year, then by the defined color order
    images = db.query(ImageRecord).order_by(ImageRecord.year_made, ImageRecord.color_tag).all()
    
    print(f"Found {len(images)} images. Generating HTML...")
    # Render the Jinja2 template with the image data
    gallery_html = templates.get_template("neocities_gallery_template.html").render({"images": images})
    
    print("Uploading to Neocities...")
    try:
        url = "https://neocities.org/api/upload"
        files = {'gallery.html': gallery_html}
        headers = {'Authorization': f'Bearer {NEOCITIES_API_KEY}'}
        
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
        
        print("Neocities gallery updated successfully.")
        return "Neocities gallery updated successfully."
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to upload to Neocities: {e.response.text if e.response else e}")
        raise HTTPException(status_code=500, detail=f"Failed to update Neocities: {e.response.text if e.response else e}")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(authenticate), db: Session = Depends(get_db)):
    """The main management dashboard."""
    images = db.query(ImageRecord).order_by(ImageRecord.uploaded_at.desc()).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "images": images,
        "color_options": [color.value for color in ColorTag]
    })

@app.post("/upload")
async def upload_image(
    request: Request,
    _=Depends(authenticate),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    title: str = Form(...),
    color_tag: ColorTag = Form(...),
    year_made: int = Form(...),
    description: Optional[str] = Form(None),
    is_sensitive: bool = Form(False)
):
    """Handles image upload, processing, and database entry."""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    file_content = await file.read()
    
    # Generate a unique filename using UUID to avoid collisions
    uuid_filename = f"{uuid.uuid4()}.webp"
    
    # Upload to Supabase
    supabase_url = upload_to_supabase(file_content, uuid_filename)
    
    # Generate markdown URL
    markdown_url = f"![{title}]({supabase_url})"
    
    # Create database record
    new_image = ImageRecord(
        uuid_filename=uuid_filename,
        original_filename=file.filename,
        title=title,
        supabase_url=supabase_url,
        markdown_url=markdown_url,
        color_tag=color_tag,
        year_made=year_made,
        description=description,
        is_sensitive=is_sensitive,
    )
    
    db.add(new_image)
    db.commit()
    
    # Trigger Neocities update
    try:
        update_neocities_gallery(db)
    except HTTPException as e:
        # Log the error but don't block the redirect
        print(f"Neocities update failed after upload, but proceeding: {e.detail}")
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.delete("/delete/{image_id}", status_code=status.HTTP_200_OK)
async def delete_image(
    image_id: int, 
    _=Depends(authenticate), 
    db: Session = Depends(get_db)
):
    """Deletes an image from the database and Supabase storage."""
    image = db.query(ImageRecord).filter(ImageRecord.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete from Supabase
    if supabase:
        try:
            supabase.storage.from_(SUPABASE_BUCKET).remove([image.uuid_filename])
        except Exception as e:
            # Log error but don't fail the whole operation if file not found
            print(f"Could not delete {image.uuid_filename} from Supabase: {e}")
    
    # Delete from database
    db.delete(image)
    db.commit()
    
    # Trigger Neocities update
    try:
        update_neocities_gallery(db)
        return {"message": "Image deleted and Neocities updated."}
    except HTTPException as e:
        return JSONResponse(
            status_code=500, 
            content={"message": "Image deleted, but Neocities update failed.", "error": e.detail}
        )

@app.post("/update-gallery")
async def manual_gallery_update_endpoint(
    _=Depends(authenticate), 
    db: Session = Depends(get_db)
):
    """Manual trigger to update the Neocities gallery."""
    try:
        message = update_neocities_gallery(db)
        return {"message": message}
    except HTTPException as e:
        raise e
