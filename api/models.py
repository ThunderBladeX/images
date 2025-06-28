import enum
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, Enum as SAEnum
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from decouple import config

# Centralized DB and model configuration
DATABASE_URL = config("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enum for color tags (belongs with the model)
class ColorTag(str, enum.Enum):
    blushred = "blushred"
    red = "red"
    orange = "orange"
    softorange = "softorange"
    lightyellow = "lightyellow"
    yellow = "yellow"
    green = "green"
    sagegreen = "sagegreen"
    skyblue = "skyblue"
    blue = "blue"
    indigo = "indigo"
    violet = "violet"
    magenta = "magenta"
    pink = "pink"
    honeybrown = "honeybrown"
    brown = "brown"
    black = "black"
    white = "white"

# SQLAlchemy model for the 'images' table
class ImageRecord(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    uuid_filename = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    title = Column(String, nullable=False)
    alt_text = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    credit_text = Column(String, nullable=True)
    credit_url = Column(String, nullable=True)
    supabase_url = Column(String, nullable=False)
    markdown_url = Column(Text, nullable=False)
    color_tag = Column(SAEnum(ColorTag, name="color_tag_enum"), nullable=False)
    year_made = Column(Integer, index=True, nullable=False)
    month_made = Column(Integer, nullable=True)
    day_made = Column(Integer, nullable=True)
    is_sensitive = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
