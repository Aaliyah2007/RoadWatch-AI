from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from routes.auth_routes import router as auth_router
from routes.report_routes import router as report_router
from routes.image_routes import router as image_router


app = FastAPI(
    title="RoadWatch AI",
    description="AI-powered road damage reporting and management system",
    version="1.0.0"
)


app.include_router(auth_router)
app.include_router(report_router)
app.include_router(image_router)


@app.get("/")
def home():
    return {
        "message": "RoadWatch AI API is running",
        "status": "success"
    }


@app.get("/db-test")
def database_test():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE()"))
        database_name = result.scalar()

    return {
        "database": database_name,
        "status": "connected"
    }
