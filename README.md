# OCR_goudot

Projet OCR

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
