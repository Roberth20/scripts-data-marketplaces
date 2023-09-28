import pandas as pd
from tqdm import tqdm
import json
import time
import requests

token = "APP_USR-388227695689600-092213-e8e2f23af8dae077d9772c339f55c4d8-1163634523"

headers = {
    'Authorization': f'Bearer {token}'
}

data = pd.read_excel("files/data.xlsx")
#cats = cats.iloc[:5, :]
    
reviews = []
for iid in tqdm(data['ID'], total=data.shape[0], desc="Parsing items"):
    url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50'
    resp = requests.get(url, headers=headers)
    try:
        resp = resp.json()
    except:
        print(resp.text)
        break
    time.sleep(0.3)
    try:
        rev = resp['reviews']
    except:
        print(resp)
        break
    if resp['paging']['total'] > 50:
        for i in range(resp['paging']['total']//50):
            url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50&offset={50*(i+1)}'
            resp2 = requests.get(url, headers=headers).json()
            try:
                rev += resp2['reviews']
            except:
                print(resp2)
                break
            time.sleep(0.3)
    if len(rev) == 0:
        continue
    for r in rev:
        tmp = {}
        tmp['ID'] = r['id']
        tmp['Item'] = iid
        tmp['rate'] = r['rate']
        tmp['content'] = r['content']
        reviews.append(tmp)
            
reviews = pd.DataFrame(reviews)
print("Saving data from products and categories")
reviews.to_excel("files/reviews.xlsx", index=False)

    
#with open("files/reviews.json", "w") as f:
 #   json.dump(reviews, f)