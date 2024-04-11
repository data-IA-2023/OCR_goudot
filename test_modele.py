import os
os.environ['DATABASE_URL']='sqlite:///test.sqlite'
if os.path.exists('test.sqlite'):
    os.remove('test.sqlite')
from modele2 import *
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
#sqlalchemy.exc.IntegrityError
import sqlalchemy, pytest

def test_0(env_bdd):
    '''
    Check BDD vide !
    '''
    assert DATABASE_URL=="sqlite:///test.sqlite"
    with Session(engine) as session:
        res=session.execute(select(Client)).all()
        assert len(res)==0

def test_Error(env_bdd):
    with Session(engine) as session:
        client = Client(id=1, name='Essai', adr='Ici', cat='X')
        session.add(client)
        #session.commit()
        client = Client(id=1, name='SameID', adr='Ici', cat='X')
        session.add(client)
        with pytest.raises(sqlalchemy.exc.IntegrityError) as excp:
            session.commit()
        assert str(excp.value)


def test_1(env_bdd):
    with Session(engine) as session:
        client = Client(id=1, name='Essai', adr='Ici', cat='X')
        session.add(client)
        #session.commit()

        query=select(Client)
        print(query)
        res=session.execute(query).all()
        assert len(res)==1

        client = Client(id=2, name='Essai2', adr='Ici', cat='Y')
        session.add(client)
        res=session.execute(query).all()
        assert len(res)==2

def test_import():
    with open('static/FAC_2019_0502-521676.png.txt', 'w') as f:
        f.write('''INVOICE FAC_2019_0502
Issue date 2019-06-01 19:02:00
Bill to Natalia Omma

Address 854, chemin Couturier
62821 Saint Roland

Process parent light field. 3 x« 62.99 Euro
Process parent light field.    B x 17.70 Euro
Address aperiam recusandae delectus. Z   «x 57.12 Euro
Story onto everybody east. 2x 59,73 Euro

TOTAL 564.27 Euro
''')
    with open('static/FAC_2019_0502-521676.pngqr.txt', 'w') as f:
        f.write('''INVOICE:FAC_2019_0502
DATE:2019-06-01 19:02:00
CUST:00337
CAT:C''')
    Facture.read_file('FAC_2019_0502-521676')
    with Session(engine) as session:
        fac = session.get(Facture, 'FAC_2019_0502-521676') # https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.Session.get
        assert fac.total==564.27
        assert fac.cumul==564.27

        assert fac.client.id==337
        assert fac.client.cat=='C'
        assert fac.client.name=='Natalia Omma'
        assert '854, chemin Couturier' in fac.client.adr
        assert '62821 Saint Roland' in fac.client.adr

        assert len(fac.commandes)==4
        assert fac.commandes[1].qty==8
        assert fac.commandes[3].produit.price==59.73
