from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, company, contact, event, health, tracked_role, user
from app.core.config import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)


@app.exception_handler(RequestValidationError)
async def validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Keep validation locations and messages while omitting submitted secrets."""
    # Validation errors can otherwise echo passwords, including an entire body.
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
                for error in exc.errors()
            ]
        },
    )


@app.middleware("http")
async def private_response_headers(request: Request, call_next):
    """Ask browsers and shared caches not to store account or private-data responses."""
    response = await call_next(request)
    if request.url.path.startswith(
        ("/auth", "/users", "/companies", "/contacts", "/tracked-roles", "/events")
    ):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def root():
    return {"message": "Hello world! From backend."}


app.include_router(health.router)
app.include_router(company.router)
app.include_router(contact.router)
app.include_router(event.router)
app.include_router(tracked_role.router)
app.include_router(user.router)
app.include_router(auth.router)
