import pyodbc
from sqlalchemy import create_engine, Column, DateTime, ForeignKey, Integer, String, Float, Date, select, update, delete, func
from sqlalchemy.orm import relationship, sessionmaker, Session, mapped_column, declarative_base
import os, dotenv, requests, datetime, json, math, subprocess, re, glob
from colorama import Fore, Back, Style

dotenv.load_dotenv()
DATABASE_URL=os.getenv('DATABASE_URL')
DISCORD=os.getenv('DISCORD_WEBHOOK')

OCR_API=os.getenv('OCR_API')
VISION_KEY=os.getenv('VISION_KEY')
VISION_ENDPOINT=os.getenv('VISION_ENDPOINT')
VISION_URL=f"{VISION_ENDPOINT}/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01"
headers = {'Accept': 'application/json'
    , 'Ocp-Apim-Subscription-Key': VISION_KEY
    , 'Content-Type': 'application/json'}

# Connection à la BDD
engine = create_engine(DATABASE_URL) # , echo=True
# classe de base dont no objets ORM vont dériver
Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    id  = Column(Integer, primary_key=True)
    name = Column(String)
    adr = Column(String)
    cat = Column(String)
    # 'factures' permet d'accéder aux factures (1..N) du clients
    factures = relationship("Facture", back_populates="client")

    def __str__(self):
        return f"CLIENT [{self.id}] {self.name} ({self.adr})"

class Facture(Base):
    __tablename__ = 'factures'
    no = Column(String(25), primary_key=True)
    dt = Column(DateTime)
    total = Column(Float)
    cumul = Column(Float)
    # client_id est la FK
    client_id = mapped_column(ForeignKey("clients.id"))
    # 'client' permet d'accéder au client lié à la facture
    client = relationship("Client", back_populates="factures")

    txt_ocr = Column(String)
    txt_qr = Column(String)
    txt_vision = Column(String)

    commandes = relationship("Commande", order_by="Commande.no", cascade="delete") # , back_populates="factures"

    def __str__(this):
        return f"FACTURE [{this.no}] {this.total}€"

    def update_vision(this):
        # Récupération des données
        image_url=OCR_API+"/"+this.no

        try:
            r = requests.post(VISION_URL, headers=headers, json={'url': image_url})
            if r.status_code==200:
                txt_vision=""
                for line in r.json()['readResult']['blocks'][0]['lines']:
                    bp=line['boundingPolygon'][0]
                    txt_vision+=f"{bp['x']}x{bp['y']} {line['text']}\n"
                    #print(f"    Line {bp['x']}x{bp['y']} : {line['text']}")
                this.txt_vision=txt_vision
            else:
                this.txt_vision = f"Status {r.status_code}, VISION_URL={VISION_URL}, image_url={image_url}"
        except Exception as e:
            this.txt_vision = f"Exception {e}..."


    # méthode de classe (avec @staticmethod)
    @staticmethod
    def read_file(no):
        '''
        Cette méthode de classe lit les informations des fichiers "static/{no}.png.txt" et "static/{no}.pngqr.txt"
        pour créer la facture, clients, commandes, produits (éventuel)
        Retourne True si création OK
        False sinon
        '''
        with Session(engine) as session:
            #query = select(Facture).where(Facture.no==no)
            fac = session.get(Facture, no)
            if fac.total!=fac.cumul:
                session.execute(delete(Facture).where(Facture.no==no)) # supprime la facture...
                session.execute(delete(Commande).where(Commande.facture_id==no)) # supprime les commandes...
            #res = session.execute(query).scalar()
            # Si la facture n'existe pas encore:
            if fac.total!=fac.cumul:
                print('---------------------------------------------------------')
                print(f'Read {no}')
                if DISCORD:
                    requests.post(DISCORD, json = {"content": f"Facture.read_file('{no}')"})
                    #pass
                x={'cust_adr':'', 'no': no, 'total': 0.0, 'cust_name':''}
                cmds=[]
                cumul=0.0
                with open(f'static/{no}.pngqr.txt') as f:
                    txt_qr=""
                    for line in f:
                        txt_qr += line
                        line=line.strip()
                        #if 'INVOICE' in line: x['no']=line[8:]
                        if 'DATE' in line: x['dt']=datetime.datetime.strptime(line[5:], r"%Y-%m-%d %X")
                        if 'CUST' in line: x['cust_id']=int(line[5:])
                        if 'CAT' in line: x['cust_cat']=line[4:]
                with open(f'static/{no}.png.txt') as f:
                    txt_ocr=""
                    adr=''
                    for line in f:
                        txt_ocr+=line
                        line=line.strip()
                        mtot=re.match(r'TOTAL ([0-9.,]+)', line)
                        mcmd=re.match(r'(.*)\. ([0-9BiTSo]+)[ «.]*x[ «]*([0-9.,]+)', line)
                        if not line: pass
                        elif 'Bill to' in line: x['cust_name']=line[8:]
                        elif 'INVOICE' in line: pass
                        elif 'Issue date' in line: pass
                        elif mtot: x['total']=round(float(mtot.group(1).replace(',', '.')), 2)
                        elif mcmd:
                            qty=mcmd.group(2)
                            if qty=='S': qty='5'
                            if qty=='B': qty='8'
                            if qty=='o': qty='9'
                            if qty=='i': qty='1'
                            if qty=='T': qty='7'
                            cmd={'name': mcmd.group(1), 'qty': int(qty), 'price': round(float(mcmd.group(3).replace(',', '.')), 2)}
                            cmds.append(cmd)
                            cumul += cmd['qty'] * cmd['price']
                        else:
                            x['cust_adr']+=line
                            print(Fore.YELLOW, '***', line, Style.RESET_ALL)

                cumul=round(cumul, 2)
                x['cust_adr']=x['cust_adr'].replace('Address ', '')
                if cumul!=x['total']:
                    print(x, cmds)
                    print(Fore.RED, '*** FACTURE total/cumul', x['total'], cumul, Style.RESET_ALL)

                client = session.get(Client, x['cust_id']) # session.execute(select(Client).where(Client.id==x['cust_id'])).scalar()
                if not client:
                    client=Client(id=x['cust_id'], name=x['cust_name'], cat=x['cust_cat'], adr=x['cust_adr'])
                    session.add(client)
                fac=Facture(no=no, dt=x['dt'], total=x['total'], cumul=cumul, txt_qr=txt_qr, txt_ocr=txt_ocr, client=client)
                idx=1
                for p in cmds:
                    #prod = session.query(Produit).get(p['name'])
                    prod = session.get(Produit, p['name'])
                    if not prod:
                        prod = Produit(name=p['name'], price=p['price'])
                        session.add(prod)
                    cmd=Commande(facture_id=fac.no, produit=prod, qty=p['qty'], no=idx)
                    idx+=1
                    session.add(cmd)
                session.add(fac)
                session.commit()
                return fac.total==fac.cumul
            #return fac # facture créee à partir des info des TXT

class Produit(Base):
    __tablename__ = 'produits'
    #__table_args__ = {'schema': 'test_goudot'}
    name = Column(String(200), primary_key=True, index=True)
    price = Column(Float)
    #factures = relationship("Facture", back_populates="client")

    def __str__(this):
        return f"PRODUIT [{this.name}] {this.price}€"

class Commande(Base):
    __tablename__ = 'commandes'
    facture_id = mapped_column(ForeignKey("factures.no"), primary_key=True)
    #facture = relationship("Facture", cascade="all, delete")
    produit_id = mapped_column(ForeignKey("produits.name"), primary_key=True)
    produit = relationship("Produit") # , back_populates="factures"
    facture = relationship("Facture")
    no = Column(Integer, primary_key=True)
    qty = Column(Integer)

    def __str__(this):
        if this.produit:
            return f"CMD{this.no} : {this.qty} x {this.produit.price:.2f}€ [{this.facture_id}, {this.produit}]" # : {this.qty*this.produit.price}€
        else:
            return f"CMD{this.no} : {this.qty} x [{this.facture_id}, {this.produit}]" # : {this.qty*this.produit.price}€

# Cette commande crée dans la BDD les tables correspondantes
Base.metadata.create_all(bind=engine)



if __name__=="__main__":

    #Facture.update_vision("FAC_2019_0003-4174848")

    fns=glob.glob('static/*.pngqr.txt')

    for no in [fn[7:-10] for fn in fns]:
        flag = Facture.read_file(no) # "FAC_2019_0003-4174848"
        if not flag:
            #Facture.update_vision(no)
            pass
    #print(fac)
    #print('DATABASE_URL=', DATABASE_URL)
    with Session(engine) as session:
        #x=session.query(func.count(Facture))
        #query=func.count(Facture)
        query = session.query(Facture).count()
        print('count', query)
        '''
        client = Client(id=1, name="Essai", adr="Ici")
        print(client)
        session.add(client)
        session.commit()
        '''

        '''
        query=select(Client).where(Client.id==1)
        print(query)
        client = session.execute(query).scalar()
        print(client)

        fac=Facture(no="FAC_2024-0000", total=0.0)
        fac.client=client
        session.add(fac)
        session.commit()


        query=select(Client)
        clients = session.execute(query).all()
        print(clients)
        for row in clients:
            client=row[0]
            print(client, client.factures)
        '''



'''
    with Session(engine) as session:
        client = Client(id=1, name="Essai")
'''
