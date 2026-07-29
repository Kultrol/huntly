from fastapi import FastAPI

from app.api import company

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello world! From backend."}


app.include_router(company.router)
