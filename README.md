# OCR_goudot

Projet OCR

# TODO
- lignes non traitées (adresses)
- ajout monitoring (date traitement)
- graphiques & vues
- commentaires à ajouter
- garder cumul ???
- ajout print N sur récup

# Environnement
**OCR_API** : https://invoiceocrp3.azurewebsites.net/invoices  
**DATABASE_URL** : sqlite:///bdd.sqlite
**VISION_KEY** : d'Azure
**VISION_ENDPOINT** : Azure


# CLI Azure
Installation : https://learn.microsoft.com/fr-fr/cli/azure/install-azure-cli  
Documentation az CLI : https://learn.microsoft.com/fr-fr/cli/azure/group?view=azure-cli-latest

Connection à Azure:
```bash
 az login
```

Création de groupe de ressources:
```bash
 RESOURCE_GROUP=ocr-goudot
 LOCATION=francecentral

 az group create --name $RESOURCE_GROUP --location $LOCATION
```

Lister les groupes de ressources (sous forme de table):
```bash
 az group list -o table
```

Liste des locations:
```bash
 az account list-locations -o table
```

Liste des SKU:
lien: [azure virtual-machines](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli) 
```bash
 az vm list-skus --location $LOCATION --size Standard_D --all --output table
```

Création VM:

```bash
 VM_NAME=vm-ocr-goudot
 VM_USERNAME=goudot
 VM_IMAGE=UbuntuLTS
 VM_SIZE=Standard_D2ads_v5

 az vm create -n $VM_NAME -g $RESOURCE_GROUP \
  --image $VM_IMAGE --size $VM_SIZE \
  --admin-username $VM_USERNAME \
  --ssh-key-values @/home/goudot/.ssh/id_rsa.pub
```

# Environnement

## Fichier .env (à partir des infos sur Vision)
__OCR_API__="https://invoiceocrp3.azurewebsites.net/invoices"  
__VISION_KEY__="XXXXXXXXXXXXXXXXXXX"  
__VISION_ENDPOINT__="https://XXXXXXXXXXXX.cognitiveservices.azure.com/"  


Création venv:
```bash
 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt
```

Execution prog:
```bash
 source venv/bin/activate
 python3 develOCR.py
```

Execution appli Flask:
```bash
 source venv/bin/activate
 uvicorn controller:app --port 3000 --host 0.0.0.0 --reload
```

Création image docker locale:
```bash
 docker build -t testocr .
```

Execution image docker locale (port 3000):
```bash
 docker rm testocr
 # opt -e : variable d'environnement
 docker run -p 3000:3000 -e MYVAR=XXX --name testocr testocr
  
```

Copie projet -> datalab:
```bash
 # Utilisation .rsyncignore
 rsync -avz --exclude-from=.rsyncignore . goudot@$DATALAB:~/OCR_goudot/
```
Sur datalab:
```bash
 docker build -t ocrprog .  
 docker rm ocrprog  
 docker run --name ocrprog \
    -p 3100:3000 \
    -e OCR_API=https://invoiceocrp3.azurewebsites.net/invoices \
    -e DATABASE_URL=sqlite:///bdd.sqlite \
    ocrprog
```

# Azure Vision API
Documentation : https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/quickstarts-sdk/image-analysis-client-library-40?tabs=visual-studio%2Clinux&pivots=programming-language-python  
OCR avec curl:
```bash
 IMG="FAC_2024_0002-2338479mod.png"
 IMAGE="https://invoiceocrp3.azurewebsites.net/invoices/FAC_2024_0002-2338479"
 IMAGE="https://app.myconnectech.fr/public/"$IMG
 curl -v -H "Ocp-Apim-Subscription-Key: $VISION_KEY" \
 -H "Content-Type: application/json" \
 "$VISION_ENDPOINT/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01" \
 -d "{'url':'$IMAGE'}" | jq > data/$IMG.json
```

Grande image 
```bash
 FN="data/FAC_2024_0270-96131.png.png"
 
 curl -v -H "Ocp-Apim-Subscription-Key: $VISION_KEY" \
 -H "Content-Type: application/json" \
 "$VISION_ENDPOINT/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01" \
 -d "{'url':'$IMAGE'}" | jq
```
## tesseract

```bash
 tesseract data/FAC_2024_0270-96131.png.png output alto
```