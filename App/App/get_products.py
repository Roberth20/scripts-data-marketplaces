import requests
import pandas as pd
from tqdm import tqdm
import json
import time
from bs4 import BeautifulSoup as bs

trends = pd.read_excel("files/trends.xlsx")

token = "APP_USR-388227695689600-092411-9e4518ec7c3d1a236d5939f57221d8c1-1163634523"

headers = {
    'Authorization': f'Bearer {token}'
}

prueba = []
for j, row_t in tqdm(trends.iterrows(), total=trends.shape[0], desc="Tendencias"):
    count = 0
    data = requests.get(row_t["url"]).text
    soup = bs(data, "lxml")
    for tag in soup.find_all('a', class_='ui-search-link', title=True, rel=False):
        if tag.h2 and "aria-label" not in tag.attrs.keys():
            id = tag['href'][33:47]
            if "MLC" not in id:
                continue
            id = id.replace("-", "")
            url = f"https://api.mercadolibre.com/items/{id}"
            response = requests.get(url, headers=headers)
            try:
                test = response.json()
            except:
                print('Hubo un error por: ', response.text)
            try:
                tmp = {}
                tmp['ID'] = test['id']
                tmp["Nombre"] = test['title']
                tmp['seller_id'] = test['seller_id']
                tmp['category'] = row_t["categoria"]
                tmp['Precio'] = test['price']
                tmp["keyword"] = row_t['keyword']
                prueba.append(tmp)
                count += 1
            except:
                if test["error"] == 'resource not found':
                    print(tag)
                else:
                    print(test)
            if count == 20:
                break
                
data = pd.DataFrame(prueba)
data.to_excel("files/data.xlsx", index=False)