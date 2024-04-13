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
Dans fichier .env:  
**OCR_API** : https://invoiceocrp3.azurewebsites.net/invoices  
**DATABASE_URL** : sqlite:///bdd.sqlite  
**VISION_KEY** : d'Azure  
**VISION_ENDPOINT** : Azure  
**DISCORD_OCR** : de discord pour poster des messages

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

# Environnement python 

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

Execution des tests:
```bash
 source venv/bin/activate
 pytest test_modele.py
```

Création image docker locale:
```bash
 docker build -t testocr .
```

Execution image docker locale (port 3000):
```bash
 docker rm testocr
 # opt -e : variable d'environnement
 #docker run -p 3000:3000 -e MYVAR=XXX -e VAR2=555 --name testocr testocr
 docker run -p 3000:3000 --env-file .env --name testocr testocr
```

# Azure

Création ACR 
```bash
 RESOURCE_GROUP=goudot
 LOCATION=francecentral
 ACR_NAME=gretap3acr
 IMAGE=testocr

 az acr create --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME --sku Basic --admin-enabled true

 # Récupération du password pour y accéder plus tard
 ACR_PASSWORD=$(az acr credential show -n $ACR_NAME | jq -r '.passwords[0].value')
 echo ACR_PASSWORD=$ACR_PASSWORD
 ```

Copie de l'image docker -> Azure ACR:
```bash
 docker login $ACR_NAME.azurecr.io 
 docker tag $IMAGE $ACR_NAME.azurecr.io/$IMAGE 
 docker push $ACR_NAME.azurecr.io/$IMAGE 
 ```

Création instance conteneur sur Azure:
```bash
 RESOURCE_GROUP=goudot
 LOCATION=francecentral
 ACR_NAME=gretap3acr
 IMAGE=ocrprog
 ECR_NAME=ocrprog-goudot
 PORT=3000
 
 az container create \
    --resource-group $RESOURCE_GROUP \
    --name $ECR_NAME \
    --image $ACR_NAME.azurecr.io/$IMAGE \
    --registry-username $ACR_NAME \
    --registry-password $ACR_PASSWORD \
    --dns-name-label $ECR_NAME \
    --ports $PORT \
    --environment-variables OCR_API="https://invoiceocrp3.azurewebsites.net/invoices" \
    --secure-environment-variables DATABASE_URL=mssql+pyodbc:///?odbc_connect=Driver%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BServer%3Dtcp%3Aocrbd.database.windows.net%2C1433%3BDatabase%3Dgoudot%3BUid%3Dmohammed%3BPwd%3Dpassword%3C%C3%A0123%3BEncrypt%3Dyes%3BTrustServerCertificate%3Dno%3BConnection+Timeout%3D30%3B


```
Documentation : https://learn.microsoft.com/en-us/cli/azure/container?view=azure-cli-latest
Visit : http://ecrp2az1.francecentral.azurecontainer.io:5000

Restart conteneur:
```bash
 az container restart \
    --resource-group $RESOURCE_GROUP \
    --name $ECR_NAME

 az container stop --resource-group goudot -n ecr-invoiceocr
 az container stop --resource-group goudot -n ocrprog-goudot
 az container stop --resource-group ocr-Berville -n instanceconteneurlb
 az container stop --resource-group ocr-jonathan -n quitbox
 az container stop --resource-group ocr-Pierre -n ecr-ocr-pierre
 az container stop --resource-group OCR-REDA -n redcontainerinstance
 az container stop --resource-group ocr-remi-t -n ecr-ocr-remi-t
 az container stop --resource-group ocr-yahya -n yahya
 az container stop --resource-group ocr-yahya -n yayaya
 az container stop --resource-group ocr_kaelig -n ocr-corr-kael
 az container stop --resource-group OCR_Mohammed -n ecr-ocr-mohammed

```

Liste des Conteneurs:
```bash
 az container list -o table
```

Logs Conteneur:
```bash
 az container logs --resource-group $RESOURCE_GROUP --name $ECR_NAME
```




Copie projet -> datalab:
```bash
 # Utilisation .rsyncignore
 TARGET=$MAME
 rsync -avz --exclude-from=.rsyncignore . goudot@$TARGET:~/OCR_goudot/
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
 #tesseract data/FAC_2024_0270-96131.png.png output alto
 tesseract static/FAC_2024_0270-96131.png stdout --psm 4
```