import math
import time
import requests

#service_url = "https://services2.arcgis.com/mJaJSax0KPHoCNB6/ArcGIS/rest/services/DRPComplianceRelProd/FeatureServer/3/"
#params = {
#    "f": "pjson",
#}

#response = requests.get(service_url, params=params, timeout=120)
#data = response.json()

#maxRecordCount = data["maxRecordCount"]

maxRecordCount = 200

base_url = "https://services2.arcgis.com/mJaJSax0KPHoCNB6/ArcGIS/rest/services/DRPComplianceRelProd/FeatureServer/3/query"

params = {
    "where": "1=1",
    "returnIdsOnly": "true",
    "f": "pjson",
}

response = requests.get(base_url, params=params, timeout=120)
data = response.json()

objectIds = data["objectIds"]
max_retries = 20
delay = 3

#for i in range(math.ceil(len(objectIds)/maxRecordCount)):
for i in range(0,10):
    ids = []
    if ((i+1)*maxRecordCount) < len(objectIds):
        ids = objectIds[i * maxRecordCount: (i * maxRecordCount) + maxRecordCount]
        print(str(i * maxRecordCount) + ":" + str((i * maxRecordCount) + maxRecordCount))
    else:
        ids = objectIds[i * maxRecordCount:]
        print(str(i * maxRecordCount) + ":" + str(len(objectIds)))

    reqQS = {
        "objectIds" : ','.join(map(str, ids)),
        "outFields" : "*",
        "f" : "geojson"
    }
    #print(reqQS)

    features = []

    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=reqQS, timeout=120)
            data = response.json()
            features.extend(data["features"])

        except Exception as e:
            print(f"Attempt {(attempt + 1)} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max retries exceeded. Exiting.")
                raise
