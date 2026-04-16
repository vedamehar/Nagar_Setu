from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./complaints.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, unique=True, index=True)
    phone_number = Column(String, index=True)
    description = Column(String)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    media_path = Column(String, nullable=True) # local path to downloaded image
    status = Column(String, default="Received")

Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
