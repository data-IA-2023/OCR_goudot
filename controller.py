from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

import dotenv, os
from modele2 import Facture, Client, engine

dotenv.load_dotenv()

# Quelles sont les variables d'env dispo ?
for env in os.environ:
    #print(env,'=', os.environ[env])
    pass

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root(request: Request, no: str = 'FAC_2024_0326-9975'):
    with Session(engine) as session:
        fac =session.get(Facture, no)
        factures = session.execute(select(Facture.no).where(Facture.total!=Facture.cumul).order_by(Facture.dt.desc()).limit(200)).all()
        return templates.TemplateResponse(
                       request=request, name="index.html", context={"fac": fac, "factures": factures}
                   )

@app.get("/vision")
def read_root(request: Request, no: str = 'FAC_2024_0326-9975'):
    with Session(engine) as session:
        fac =session.get(Facture, no)
        fac.update_vision()
        session.commit()
        return RedirectResponse("/?no="+no)


@app.get("/updates")
def read_root(request: Request):
    res = modele.Facture.extract('2024-01-01')
    return res
