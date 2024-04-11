from sqlalchemy import create_engine, Column, DateTime, ForeignKey, Integer, String, Float, Date, select, update, delete, func
from sqlalchemy.orm import relationship, sessionmaker, Session, mapped_column, declarative_base
import os, dotenv, requests, datetime, json, math, subprocess, re, glob

dotenv.load_dotenv()
DATABASE_URL=os.getenv('DATABASE_URL')
DISCORD=os.getenv('DISCORD_WEBHOOK')
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
    no = Column(String, primary_key=True)
    dt = Column(DateTime)
    total = Column(Float)
    cumul = Column(Float)
    # client_id est la FK
    client_id = mapped_column(ForeignKey("clients.id"))
    # 'client' permet d'accéder au client lié à la facture
    client = relationship("Client", back_populates="factures")

    txt_ocr = Column(String)
    txt_qr = Column(String)

    commandes = relationship("Commande", order_by="Commande.no", cascade="delete") # , back_populates="factures"

    def __str__(this):
        return f"FACTURE [{this.no}] {this.total}€"

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
            query = select(Facture).where(Facture.no==no)
            session.execute(delete(Facture).where(Facture.no==no)) # supprime la facture...
            session.execute(delete(Commande).where(Commande.facture_id==no)) # supprime les commandes...
            res = session.execute(query).scalar()
            # Si la facture n'existe pas encore:
            if not res:
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
                        mcmd=re.match(r'(.*)\. ([0-9B]+) *x *([0-9.,]+)', line)
                        if not line: pass
                        elif 'Bill to' in line: x['cust_name']=line[8:]
                        elif 'INVOICE' in line: pass
                        elif 'Issue date' in line: pass
                        elif mtot: x['total']=round(float(mtot.group(1).replace(',', '.')), 2)
                        elif mcmd:
                            qty=mcmd.group(2)
                            if qty=='B': qty='8'
                            cmd={'name': mcmd.group(1), 'qty': int(qty), 'price': round(float(mcmd.group(3).replace(',', '.')), 2)}
                            cmds.append(cmd)
                            cumul += cmd['qty'] * cmd['price']
                        else:
                            x['cust_adr']+=line
                            print('***', line)

                #print(txt_qr)
                print('---------------------------------------------------------')

                #print(txt_ocr)
                print(x, cmds)
                cumul=round(cumul, 2)
                print(x['total'], cumul)
                x['cust_adr']=x['cust_adr'].replace('Address ', '')

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
                return True
            #return fac # facture créee à partir des info des TXT

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

    with Session(engine) as session:
        client = Client(id=-1, name='Essai', adr='Ici', cat='X')
        print(str(client))

    quit()

    fns=glob.glob('static/*.txt')
    fns=[fn[7:-10] for fn in fns if '.pngqr.txt' in fn]
    #print(fns)

    for no in fns[:10000]:
        fac = Facture.read_file(no) # "FAC_2019_0003-4174848"
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
