from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

class FileCache(Base):
    __tablename__ = 'file_cache'
    id = Column(Integer, primary_key=True)
    track_id = Column(String, unique=True)
    file_id = Column(String)  # Telegram's unique ID for the file
    quality = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Run this once to create the database
def init_db():
    Base.metadata.create_all(engine)
