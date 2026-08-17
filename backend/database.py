from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus

# Enter your MySQL root password here
MYSQL_PASSWORD = "YOUR_ACTUAL_PASSWORD"

# Safely encode special characters such as @ in the password
DATABASE_URL = (
    "mysql+pymysql://root:"
    + quote_plus("A@liyah2007")
    + "@localhost:3306/roadwatch_db"
)

engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()