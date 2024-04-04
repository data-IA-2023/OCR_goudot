from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float, Date, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import create_engine

import os, dotenv, requests, datetime, json, math, subprocess, re

dotenv.load_dotenv()
BDD_URL=os.getenv('DATABASE_URL', 'sqlite:///test.sqlite')
OCR_API=os.getenv('OCR_API')
VISION_KEY=os.getenv('VISION_KEY')
VISION_ENDPOINT=os.getenv('VISION_ENDPOINT')
VISION_URL=f"{VISION_ENDPOINT}/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01"

headers = {'Accept': 'application/json'
         , 'Ocp-Apim-Subscription-Key': VISION_KEY
         , 'Content-Type': 'application/json'}

engine = create_engine(BDD_URL) # , echo=True

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    #__table_args__ = {'schema': 'test_goudot'}
    id  = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    adr = Column(String)
    cat = Column(String)
    factures = relationship("Facture", back_populates="client")

    def __str__(this):
        return f"CLIENT [{this.id}] {this.name}"

class Produit(Base):
    __tablename__ = 'produits'
    #__table_args__ = {'schema': 'test_goudot'}
    name = Column(String, primary_key=True, index=True)
    price = Column(Float)
    #factures = relationship("Facture", back_populates="client")

    def __str__(this):
        return f"PRODUIT [{this.name}]"

class Commande(Base):
    __tablename__ = 'commandes'
    facture_id = mapped_column(ForeignKey("factures.no"), primary_key=True)
    #facture = relationship("Facture", back_populates="commandes")
    produit_id = mapped_column(ForeignKey("produits.name"), primary_key=True)
    qty = Column(Integer)

    def __str__(this):
        return f"CMD {this.qty} x [{this.facture_id}, {this.produit_id}]"


class Facture(Base):
    __tablename__ = 'factures'
    #__table_args__ = {'schema': 'test_goudot'}
    no = Column(String, primary_key=True, index=True)
    dt = Column(DateTime)
    total = Column(Float)
    cumul = Column(Float)
    client_id = mapped_column(ForeignKey("clients.id"))
    client = relationship("Client", back_populates="factures")

    def __str__(this):
        return f"FACTURE [{this.no}] {this.total}€"

    @staticmethod
    def extract(start_date):
        try:
            r = requests.get(OCR_API+"?start_date="+start_date, headers=headers)
            invoices = r.json()['invoices']
        except:
            invoices=[{'no': 'FAC_2024_0172-2382800', 'dt':'2024-02-25 00:00:00'}, {'no': 'FAC_2024_0170-3509674', 'dt': '2024-02-25 02:58:00'}]
        N=0
        with Session(engine) as session:
            for doc in invoices:
                no=doc['no']
                #print(doc)
                # Traitement OCR

                fn=f"static/{no}.png"

                fac = session.execute(select(Facture).where(Facture.no == no)).scalar()
                if fac:
                    print(f"Facture {no} déjà traitée !")
                    continue

                # Récupération image si pas présente
                IMAGE_URL=OCR_API+"/"+no
                if not os.path.exists(fn):
                    print(f"Récup {fn}")
                    r = requests.get(IMAGE_URL, headers=headers)
                    if r.status_code!=200: # pas la peine de continuer si l'image n'est pas récupérée !!!
                        continue
                    #print(r.content)
                    with open(fn, "wb") as f:
                        f.write(r.content)

                # Utilisation tesseract --psm 4
                if not os.path.exists(fn+".txt"):
                    print(f"tesseract {fn}.txt")
                    with open(fn+".txt", "w") as f:
                        subprocess.run(["tesseract", fn, "stdout", "--psm", "4"], stdout=f) # tesseract data/FAC_2024_0172-2382800.png stdout --psm 4
                # Récupération QR
                if not os.path.exists(fn+"qr.txt"):
                    with open(fn+"qr.txt", "w") as f:
                        subprocess.run(["zbarimg", '--raw', fn], stdout=f) # tesseract data/FAC_2024_0172-2382800.png stdout --psm 4

                bill={'cust': '', 'no': no, 'prod': [], 'cumul': 0.0, 'total': 0.0, 'adr':''}

                with open(fn+"qr.txt", "r") as f:
                    for line in f:
                        if 'CUST:' in line: bill['custid']=int(line[5:])
                        if 'CAT:' in line: bill['cat']=line[4:5]


                with open(fn+".txt", "r") as f:
                    nl=1
                    for line in f:
                        if not line: continue
                        if 'Bill to' in line: bill['cust']=line[8:-1]
                        if 'Address' in line: bill['adr']=line[8:]+next(f)
                        m=re.match(r'TOTAL *([0-9.]+)', line)
                        if m:
                            bill['total']=float(m.group(1))
                        m=re.match(r'^([^.]*).*([0-9]+) *x *([0-9.]+)', line)
                        if m:
                            print(m.group(1), '/', m.group(2), '/', m.group(3))
                            bill['prod'].append({'name': m.group(1), 'qty': m.group(2), 'price': m.group(3)})
                            bill['cumul'] += int(m.group(2)) * float(m.group(3))

                print("***" if bill['cumul']!=bill['total'] else '', bill)

                dt = datetime.datetime.strptime(doc['dt'], r"%Y-%m-%d %X")
                client = session.execute(select(Client).where(Client.id == bill['custid'])).scalar()
                if not client:
                    client=Client(id=bill['custid'], name=bill['cust'], adr=bill['adr'], cat=bill['cat'])
                    session.add(client)
                    session.commit()
                print(client)

                fac = session.execute(select(Facture).where(Facture.no == bill['no'])).scalar()
                if not fac:
                    fac=Facture(no=no, dt=dt, total=bill['total'], cumul=bill['cumul'], client_id=client.id)
                    #fac=Facture(no=no, dt=dt, total=bill['total'], client=client)
                    session.add(fac)
                    N+=1
                print(fac)

                for prod in bill['prod']:
                    produit = session.execute(select(Produit).where(Produit.name == prod['name'])).scalar()
                    if not produit:
                        produit=Produit(name=prod['name'], price=prod['price'])
                        session.add(produit)
                    print(produit)
                    cmd = session.execute(select(Commande).where(Commande.produit_id == produit.name).where(Commande.facture_id==fac.no)).scalar()
                    if not cmd:
                        cmd=Commande(produit_id=produit.name, facture_id=fac.no, qty=prod['qty'])
                        session.add(cmd)
                    print(cmd)



                '''
                fnj=f"data/{no}.png.json"
                IMAGE_URL=OCR_API+"/"+no
                if not os.path.exists(fnj):
                    r = requests.post(VISION_URL, headers=headers, json={'url': IMAGE_URL})
                    print('OCR', fnj, r.status_code)
                    with open(fnj, "w") as f:
                        f.write(json.dumps(r.json(), indent=4))
                dt = datetime.datetime.strptime(doc['dt'], r"%Y-%m-%d %X")
                bill={'no': no, 'dt':dt, 'prod':[]}
                with open(fnj) as f:
                    res=json.load(f)
                    #print(res)
                    for line in res['readResult']['blocks'][0]['lines']:
                        bp=line['boundingPolygon'][0]
                        txt=line['text']
                        x=int(bp['x'])
                        y=bp['y']
                        nl=round(y/20.0)
                        print(f"    Line {x} x {y} : {nl} : {txt}")
                        if nl==4: bill['cust']=txt[8:]
                        if nl==6: bill['adr']=txt[8:]
                        if nl==7: bill['adr']+='\n'+txt
                        if nl>9:
                            np=nl-10 # n° produit
                            if np not in bill['prod']: bill['prod'].append({'name':'', 'qty': 0, 'price':0.0})
                            if x<50:
                                bill['prod'][np]['name']=txt
                            elif x>520: bill['prod'][np]['price']=txt.split(' ')[0]
                            else: bill['prod'][np]['qty']=txt
                    #print('BILL')
                    for x in bill['prod']:
                        if x['name']=='TOTAL':
                            x['name']=''
                            bill['total']=x['price']
                    #print(json.dumps(bill, indent=2))
                    print(bill)
                    for x in bill['prod']:
                        if x['name']:
                            produit = session.execute(select(Produit).where(Produit.name == x['name'])).first()
                            if not produit:
                                produit=Produit(name=x['name'], price=x['price'])
                                session.add(produit)
                '''

                '''
                client = session.execute(select(Client).where(Client.name == bill['cust'])).first()
                if not client:
                    client=Client(name=bill['cust'], adr=bill['adr'])
                    session.add(client)


                fac = session.execute(select(Facture).where(Facture.no == bill['no'])).first()
                #print(doc, res)
                if not fac:
                    print('ajout', doc)
                    fac=Facture(no=no, dt=dt, total=bill['total'])
                    session.add(fac)
                    N+=1
                #fac['total'] = bill['total']
                '''

            session.commit()
        result=f"{N} factures ajoutées !"
        return result


Base.metadata.create_all(bind=engine)

#Facture.extract('2019-01-01')
#Facture.extract('2019-06-01')
Facture.extract('2024-04-01')

'''
with Session(engine) as session:
    client=Client(id=1, name="Tester", adr="inconnu", cat="X")
    session.add(client)
    session.commit()
'''
