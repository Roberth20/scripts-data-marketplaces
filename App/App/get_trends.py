import pandas as pd
from tqdm import tqdm
import json
import time
import requests

token = "APP_USR-388227695689600-092411-9e4518ec7c3d1a236d5939f57221d8c1-1163634523"

headers = {
    'Authorization': f'Bearer {token}'
}
cats = pd.read_json("files/cats_mlc.json")
    
tendencias = []
for i, row_c in tqdm(cats.iterrows(), total=cats.shape[0], desc="Parsing categories"):
    count = 0
    url = f'https://api.mercadolibre.com/trends/MLC/{row_c["ID"]}'
    result = requests.get(url, headers=headers)
    try:
        result = result.json()
    except:
        print(result)
    try:
        trends = pd.DataFrame(result)
        trends["categoria"] = row_c['Name']
        if trends.shape[0] > 10:
            trends = trends.iloc[:10, :]
        tendencias.append(trends)
    except:
        if result['error'] != "Not found":
            print(result)
            
print("Saving data from products and categories")
tendencias = pd.concat(tendencias)
tendencias.reset_index(drop=True, inplace=True)
tendencias.drop_duplicates("url", inplace=True)
tendencias.to_excel("files/trends.xlsx", index=False)

    
#with open("files/reviews.json", "w") as f:
 #   json.dump(reviews, f)