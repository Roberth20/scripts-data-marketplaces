import datetime
import urllib
from hashlib import sha256
from hmac import HMAC
import json
import requests

# Creamos funcion de ayuda
def get_response_falabella(parameters: dict, API_KEY): 
    """Funcion de ayuda para contruir el endpoint de la API y para la generacion de la
    signature key.
    
    Input : 
    -------
    * parameters : dict, Diccionario con los parametros necesarios para el endpoint deseado.
    
    Return : 
    --------
    * str : sting de formato json con la respuesta."""
    concatenated = urllib.parse.urlencode(sorted(parameters.items()))
    # Creacion de la signature key
    parameters['Signature'] = HMAC(API_KEY.encode("utf-8"), msg=concatenated.encode("utf-8"), digestmod = sha256).hexdigest()
    url = urllib.parse.urlencode(sorted(parameters.items()))
    base = "https://sellercenter-api.falabella.com?"

    headers = {"User-Agent": f"{parameters['UserID']}/Python/3.9.12"}

    return requests.get(base+url, headers=headers)


def category_tree_falabella(categories: list, tree: list):
    """Funcion generadora del arbol de categorias.
    
    Input : 
    -------
    * categories : list, objeto tipo lista que contiene las categorias en forma de 
    diccionario.
    * tree : list, objeto para almacenar los datos obtenidos
    
    Return :
    --------
    None
    """
    for item in categories:
        # Para cada categoria guardamos el id y el nombre.
        tree.append({"Name": item["Name"], "Id" :item["CategoryId"]})
        # En el caso que la misma tenga subcategorias
        if type(item["Children"]) != dict:
            continue
        if type(item["Children"]["Category"]) == dict:
            tree.append({"Name": item["Children"]["Category"]["Name"], "Id": item["Children"]["Category"]["CategoryId"]})
            continue
        # Llamamos la funcion nuevamente
        category_tree_falabella(item["Children"]["Category"], tree)