import requests
# Definimos una funcion que nos ayude a construir el arbol de categorias
def category_tree(categories: list, tree: list):
    """Funcion para construccion del arbol de categorias.
    
    Input : 
    --------
    * categories : list, lista con diccionarios con informacion de cada 
    categoria.
    * tree : list, Objeto para almacenar los datos.
    
    Output : 
    ---------
    None
    """
    for item in categories:
        # Para cada item, obtenemos la informacion individual
        base_url = f"https://api.mercadolibre.com/categories/{item['id']}"
        message = requests.get(base_url).json()
        try:
            tree.append({"Name": " - ".join([i['name'] for i in message['path_from_root']]), "ID": message['id']})
        except:
            tree.append({"Name": message['name'], "ID": message['id']})
        # Si la categoria tiene subcategorias, se llama la funcion de nuevo.
        if len(message["children_categories"]) > 0:
            sub_cat = message["children_categories"]
            category_tree(sub_cat, tree)
