from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

# from app.api import company

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=False,
)


@app.get("/")
def root():
    return {"message": "Hello world! From backend."}


app.include_router(health.router)

# app.include_router(company.router)
