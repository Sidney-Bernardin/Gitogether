from fastapi import Request, APIRouter

from app.dependencies import SessionAuth, templates
from app.routes import login, repositories

router = APIRouter(tags=["pages"])
router.include_router(login.router)
router.include_router(repositories.router)


@router.get("/")
def home(req: Request, session: SessionAuth):
    return templates.TemplateResponse("pages/home.html", {"request": req, "session": session})
