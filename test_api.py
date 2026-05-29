import requests

API_URL = "https://api.data.stats.govt.nz/rest/data/STATSNZ,CEN18_HAD_001,1.0/999999.9999+999999+DHB9999.9999.9999.9.?dimensionAtObservation=AllDimensions"

headers = {
    "Ocp-Apim-Subscription-Key": "4438fa53f1e54ed093d06793b131e0b8",
    "Accept": "application/json"
}

response = requests.get(API_URL, headers=headers)

print("Status:", response.status_code)

if "application/json" in response.headers.get("Content-Type", ""):
    print(response.json())
else:
    print(response.text[:500])