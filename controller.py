from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

import dotenv, os, modele
from modele import Facture, Client, engine

dotenv.load_dotenv()

# Quelles sont les variables d'env dispo ?
for env in os.environ:
    #print(env,'=', os.environ[env])
    pass

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root(request: Request, no: str = 'FAC_2024_0326-9975', cust: str=''):
    with Session(engine) as session:
        fac = session.execute(select(Facture).where(Facture.no == no)).scalar()
        factures = session.execute(select(Facture.no).limit(10)).all()
        if cust:
            customers=session.execute(select(Client.name, Client.id).where(Client.name.like(f"%{cust}%"))).all()
        else:
            customers=[]
        return templates.TemplateResponse(
                       request=request, name="index.html", context={"fac": fac, "factures": factures, "customers":customers}
                   )

@app.get("/updates")
def read_root(request: Request):
    res = modele.Facture.extract('2024-01-01')
    return res
