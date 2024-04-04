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
        return f"PRODUIT [{this.name}] {this.price}€"

class Commande(Base):
    __tablename__ = 'commandes'
    facture_id = mapped_column(ForeignKey("factures.no"), primary_key=True)
    #facture = relationship("Facture", back_populates="commandes")
    produit_id = mapped_column(ForeignKey("produits.name"), primary_key=True)
    produit = relationship("Produit") # , back_populates="factures"
    qty = Column(Integer)

    def __str__(this):
        return f"CMD {this.qty} x [{this.facture_id}, {this.produit}]" # : {this.qty*this.produit.price}€


class Facture(Base):
    __tablename__ = 'factures'
    #__table_args__ = {'schema': 'test_goudot'}
    no = Column(String, primary_key=True, index=True)
    dt = Column(DateTime)
    total = Column(Float)
    cumul = Column(Float)
    client_id = mapped_column(ForeignKey("clients.id"))
    client = relationship("Client", back_populates="factures")

    commandes = relationship("Commande") # , back_populates="factures"

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
                    #print(f"Facture {no} déjà traitée !")
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
                    subprocess.run(["convert", fn, "-fill", "White", "-draw", "rectangle 500,0 900,150", f"static/{no}mod.png"]) # tesseract data/FAC_2024_0172-2382800.png stdout --psm 4
                    with open(fn+".txt", "w") as f:
                        subprocess.run(["tesseract", f"static/{no}mod.png", "stdout", "--psm", "4"], stdout=f) # tesseract data/FAC_2024_0172-2382800.png stdout --psm 4
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
                        m=re.match(r'TOTAL *([0-9.,]+)', line)
                        if m:
                            bill['total']=float(m.group(1).replace(',', '.'))
                        m=re.match(r'^([^.]*).*([STi0-9]+)[d\.]? *x[«]? *([0-9][0-9.,]*)', line)
                        if m:
                            qty=m.group(2)
                            if qty=='T': qty='7'
                            if qty=='S': qty='5'
                            if qty=='i': qty='1'
                            price=m.group(3).replace(',', '.')
                            print(m.group(1), '/', qty, '/', price)
                            bill['prod'].append({'name': m.group(1), 'qty': qty, 'price': price})
                            bill['cumul'] += int(qty) * float(price)
                        else:
                            if 'Address' in line: bill['adr']=line[8:]+next(f)

                print("***" if bill['cumul']!=bill['total'] else '', bill)

                dt = datetime.datetime.strptime(doc['dt'], r"%Y-%m-%d %X")
                client = session.execute(select(Client).where(Client.id == bill['custid'])).scalar()
                if not client:
                    client=Client(id=bill['custid'], name=bill['cust'], adr=bill['adr'], cat=bill['cat'])
                    session.add(client)
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
                session.commit()

        result=f"{N} factures ajoutées !"
        return result

Base.metadata.create_all(bind=engine)

Facture.extract('2019-01-01')
Facture.extract('2019-06-01')
Facture.extract('2024-04-01')

