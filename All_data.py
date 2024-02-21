import json
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from SQL.connection import conn
#from sqlalchemy.orm import Session
from SQL.models import TrendingItems, Auth, Reviews
from datetime import date, datetime
import logging
from sqlalchemy import insert
import sqlalchemy as db
import sys
from bs4 import BeautifulSoup as bs
from tqdm import tqdm
import time
from sys import argv

script, start_date, end_date = argv

start_date = pd.to_datetime(start_date, dayfirst=True).date()
end_date = pd.to_datetime(end_date, dayfirst=True).date()

try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = test

with conn.connect() as con:
    cats = pd.read_sql("SELECT * FROM Categorias", con)
    cats = cats[~cats.name.str.contains('-')]
    auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]
    if auth['expires_in'] < datetime.now():
        logging.warning("Token vencido. Intentando actualizar...")
        headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
        }
        data = json.dumps({
            'grant_type':'refresh_token',
            'client_id': config.APP_ID,
            'client_secret': config.CLIENT_SECRET,
            'refresh_token':auth['refresh_token']
        })
        response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=data)
        if not response:
            logging.error(f"The was an error retrieving the token. {response}")
            sys.exit(0)
        data = response.json()
        stmt = (
            insert(Auth).
            values(access_token=data['access_token'], expires_in = datetime.now() + pd.Timedelta("6H"),
                  refresh_token=data['refresh_token'])
        )
        con.execute(stmt)
        con.commit() 

        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]

    token = auth["access_token"]
    headers = {
        'Authorization': f'Bearer {token}'
    }

tendencias = []
for i, row_c in tqdm(cats.iterrows(), total=cats.shape[0], desc="Obteniendo tendencias..."):
    count = 0
    url = f'https://api.mercadolibre.com/trends/MLC/{row_c["id"]}'
    result = requests.get(url, headers=headers)
    try:
        result = result.json()
    except:
        logging.error(result)
        sys.exit(0)
    if type(result) != list:
        if 'error' in result.keys():
            if result['error'] ==  'Not found':
                continue
            else:
                logging.error(result)
        else:
            logging.error(result)
    try:
        trends = pd.DataFrame(result)
        if trends.shape[0] > 10:
            trends = trends.iloc[:10, :]
    except:
        print(result)
        sys.exit(0)

    trends["category"] = row_c['name']
    tendencias.append(trends)

logging.info("Guardando tendencias")
tendencias = pd.concat(tendencias)
tendencias.reset_index(drop=True, inplace=True)
tendencias.drop_duplicates("url", inplace=True)
tendencias['date'] = date.today()
trends = tendencias.drop("url", axis=1)
trends.columns = ['keywords', 'category', 'date']
with conn.connect() as con:
    trends.to_sql('Tendencias', con, index=False, if_exists='append')
    con.commit()

major_data = []
for j, row in tqdm(tendencias.iterrows(), total=tendencias.shape[0], desc="Cargando datos de productos..."):
    prueba = []
    count = 0
    data = requests.get(row["url"]).text
    soup = bs(data, "lxml")
    for tag in soup.find_all('a', class_='ui-search-link', title=True, rel=False):
        if tag.h2 and "aria-label" not in tag.attrs.keys():
            id = tag['href'][33:47]
            if "MLC" not in id:
                continue
            id = id.replace("-", "")
            url = f"https://api.mercadolibre.com/items/{id}"
            response = requests.get(url, headers=headers)
            # To prevent Too many requests error, pause the program after each request
            time.sleep(0.5)
            try:
                test = response.json()
            except:
                logging.error(f'Hubo un error por: {response.text}')
                sys.exit(0)
            if 'error' in test.keys():
                #logging.error(f'Hubo un error por: {test["error"]}, {tag}')
                continue

            tmp = {}
            tmp['ID'] = test['id']
            if len(test['title']) > 80:
                tmp['Nombre'] =  test['title'][:78]
            else:
                tmp["Nombre"] = test['title']
            tmp['seller_id'] = test['seller_id']
            tmp['Precio'] = test['price']
            tmp["keyword"] = row['keyword']
            try:
                tmp["Cantidad de ventas"] = test['sold_quantity']
            except:
                #logging.warning(f"Sin registro de ventas: {test['id']}.")
                tmp['Cantidad de ventas'] = 0
            try:
                tmp['Fecha de publicacion'] = test['start_time']
            except:
                #logging.warning(f'Sin fecha de publicacion, cambiando por fecha de creacion para producto {test["id"]}')
                tmp['Fecha de publicacion'] = test['date_created']    
            urlv = f"https://api.mercadolibre.com/items/visits?ids={id}&date_from={start_date}&date_to={end_date}"
            # Temporalmente (11-01-2024) las visitas por fecha dan problemas, cambiando a totales
            #urlv = f"https://api.mercadolibre.com/visits/items?ids={id}"
            try:
                v = requests.get(urlv, headers=headers).json()
                #tmp['visitas'] = v[id]
                tmp['visitas'] = v[0]['total_visits']
            except:
               # print(v, id)
                logging.warning(f"Hubo un error con las visitas: {v}. Igualando a cero.")
                tmp['visitas'] = 0
            tmp['Calidad'] = test['health']
            tmp['cat'] = row['category']
            prueba.append(tmp)
            count += 1

            if count == 20:
                break
                    
    major_data.append(pd.DataFrame(prueba))

major_data = pd.concat(major_data, ignore_index=True)
try:
    major_data.columns = ["item_id", "name", "seller_id", "price", "keyword", "items_sold", "publication_date", 
                              "visits", "quality", 'category']
except:
    print(major_data.head())

logging.info('Guardando datos de productos y generando documento.')
major_data['publication_date'] = pd.to_datetime(major_data['publication_date']).dt.date
major_data.fillna(0, inplace=True)
major_data.reset_index(drop=True, inplace=True)
major_data.drop_duplicates(inplace=True)
with conn.connect() as con:
    major_data.to_sql("ProductosYTendencias", con, index=False, if_exists='append')
    con.commit()

major_data.to_excel('ProductosTendencia.xlsx', index=False)

#reviews = []
#for j, row in tqdm(tendencias.iterrows(), total=tendencias.shape[0], desc="Cargando datos de opiniones..."):
#    data = requests.get(row["url"]).text
 #   soup = bs(data, "lxml")
  #  for tag in soup.find_all('a', class_='ui-search-link', title=True, rel=False):
   #     time.sleep(0.5)
    #    if tag.h2 and "aria-label" not in tag.attrs.keys():
     #       id = tag['href'][33:47]
      #      if "MLC" not in id:
       #         continue
        #    id = id.replace("-", "")
         #   url2 = f'https://api.mercadolibre.com/reviews/item/{id}?limit=50'
          #  resp = requests.get(url2, headers=headers)
           # try:
            #    resp = resp.json()
            #except:
             #   logging.error(f"Error obteniendo datos del item: {resp.text}")
              #  sys.exit(0)
            #try:
             #   rev = resp['reviews']
            #except:
             #   if resp['error'] != 'unauthorized_scopes':
              #      logging.error(f"Error obteniendo datos del item: {resp}")
               #     sys.exit(0)
                #continue

#            if resp['paging']['total'] > 50:
 #               logging.info(f"Item with {id} has {resp['paging']['total']}, retrieving first 50.")
                #err = False
                #for k in range(resp['paging']['total']//50):
                 #   time.sleep(0.5)
                  #  url = f'https://api.mercadolibre.com/reviews/item/{id}?limit=50&offset={50*(k+1)}'
                   # resp2 = requests.get(url, headers=headers).json()
                    #try:
                     #   rev += resp2['reviews']
                    #except:
                     #   if not err:
                      #      logging.error(f"Error obteniendo datos de opiniones: {resp2}")
                       #     err = True
                        #pass
                        
#            if len(rev) == 0:
 #               continue
  #          for r in rev:
   #             tmp_r = {}
    #            tmp_r['ID'] = r['id']
     #           tmp_r['Item'] = id
      #          tmp_r['rate'] = r['rate']
       #         tmp_r['content'] = r['content']
        #        reviews.append(tmp_r)
            
#logging.info("Guardando las opiniones")
#reviews = pd.DataFrame(reviews)
#reviews.columns = ['id', 'item_id', 'rate', 'content']
#reviews.fillna(0, inplace=True)
#with conn.connect() as con:
 #   stmt = (db.select(Reviews)
  #          .where(Reviews.item_id == TrendingItems.item_id))
   # revs = pd.read_sql(stmt, con)
    #diff = reviews[~reviews['id'].astype('str').isin(revs['id'])].copy()
    #diff.drop_duplicates(inplace=True)
    #if diff.shape[0] > 0:
     #   diff.to_sql("Opiniones", con, if_exists="append", index=False)
    #con.commit()

#reviews.to_excel('Opiniones.xlsx', index=False)
logging.info('Proceso finalizado.')
