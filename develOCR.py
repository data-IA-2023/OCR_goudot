#from azure.ai.vision.imageanalysis import ImageAnalysisClient
#from azure.ai.vision.imageanalysis.models import VisualFeatures
#from azure.core.credentials import AzureKeyCredential
import requests, json, dotenv, os
from PIL import Image

dotenv.load_dotenv()

OCR_API=os.getenv('OCR_API')
VISION_KEY=os.getenv('VISION_KEY')
VISION_ENDPOINT=os.getenv('VISION_ENDPOINT')
VISION_URL=f"{VISION_ENDPOINT}/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01"

headers = {'Accept': 'application/json'
         , 'Ocp-Apim-Subscription-Key': VISION_KEY
         , 'Content-Type': 'application/json'}

# Lecture liste factures pour 2024 (start_date=2024-01-01)
r = requests.get(OCR_API+"?start_date=2024-01-01", headers=headers)
#print(json.dumps(r.json(), indent=4))

for doc in r.json()['invoices']:
    print(doc)
    fn=f"data/{doc['no']}.png"
    IMAGE_URL=OCR_API+"/"+doc['no']
    # Récupération image si pas présente
    if not os.path.exists(fn):
        r = requests.get(IMAGE_URL, headers=headers)
        #print(r.content)
        with open(fn, "wb") as f:
            f.write(r.content)
    fnj=fn+".json"
    if not os.path.exists(fnj):
        r = requests.post(VISION_URL, headers=headers, json={'url': IMAGE_URL})
        #print(r.status_code)
        with open(fnj, "w") as f:
            f.write(json.dumps(r.json(), indent=4))
    with open(fnj) as f:
        res=json.load(f)
        #print(res)
        for line in res['readResult']['blocks'][0]['lines']:
            bp=line['boundingPolygon'][0]
            print(f"    Line {bp['x']}x{bp['y']} : {line['text']}")

'''
im = Image.open(fn)
print(im.size)
im2 = im.resize((850*2, 1100*2))
print(im2.size)
im2.save(fn+".png", "png") # , quality=100, optimize=True
'''
quit()










# Set the values of your computer vision endpoint and computer vision key
# as environment variables:
try:
    endpoint = os.environ["VISION_ENDPOINT"]
    key = os.environ["VISION_KEY"]
except KeyError:
    print("Missing environment variable 'VISION_ENDPOINT' or 'VISION_KEY'")
    print("Set them before running this sample.")
    exit()

# Create an Image Analysis client
client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

# Get a caption for the image. This will be a synchronously (blocking) call.
result = client.analyze_from_url(
    image_url="https://invoiceocrp3.azurewebsites.net/invoices/FAC_2024_0002-2338479",
    visual_features=[VisualFeatures.CAPTION, VisualFeatures.READ],
    gender_neutral_caption=True,  # Optional (default is False)
)

print("Image analysis results:")
# Print caption results to the console
print(" Caption:")
if result.caption is not None:
    print(f"   '{result.caption.text}', Confidence {result.caption.confidence:.4f}")

# Print text (OCR) analysis results to the console
print(" Read:")
if result.read is not None:
    for line in result.read.blocks[0].lines:
        print(f"   Line: '{line.text}', Bounding box {line.bounding_polygon}")
        for word in line.words:
            print(f"     Word: '{word.text}', Bounding polygon {word.bounding_polygon}, Confidence {word.confidence:.4f}")

#print(result)

with open('data/FAC_2024_0002-2338479.json', 'w') as f:
    f.write(str(result))

