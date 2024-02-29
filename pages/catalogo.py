import dash
from dash.exceptions import PreventUpdate
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc
from dash import html
import dash_bootstrap_components as dbc
from SQL.connection import conn
from dash import dash_table

#---------------------------#
# Setting up the page on the App
dash.register_page(__name__, path="/catalogo", name="Busqueda por catalogo")

#---------------------------#
# Making the layout
layout = html.Div([
    dbc.Row(dbc.Col(html.H2(children='Busqueda de catalogo'), width=12), justify='center'),
    dbc.Row(dbc.Col(html.P('Escriba una nueva busqueda de producto, luego, seleccione el producto para analizar el catalogo'))),
    dbc.Row(dbc.Col(dcc.Input(id='input_query', type='text', placeholder='Busqueda', debounce=True, style={'width':'45vw'}), width=6), justify='center'),
    dbc.Row(dbc.Col(html.Br())),
    dbc.Row(dbc.Col(html.Div(id='output')))
])

#---------------------------#
# Building the callbacks
@callback(Output('output', 'children'), Input('input_query', 'value'))
def search_query(query):
    # Prevent first update
    if query == None:
        raise PreventUpdate
    # Get access token
    with conn.connect() as con:
        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]
        token = auth["access_token"]
    headers = {
        'Authorization': f'Bearer {token}'
    }
    # Create the DataFrame for the new search
    df = pd.DataFrame(columns=['Nombre', 'Precio', 'Catalogo', 'Visitas', 'URL'])
    # Request the product query with specific parameters for Mercado Libre Chile and with active products
    site_id = 'MLC'
    # Requesting the products with catalog
    url = f'https://api.mercadolibre.com/sites/{site_id}/search?q={query}&catalog_listing=true&offset={0}'
    response = requests.get(url, headers=headers).json()
    # Check for error messages
    if 'message' in response.keys():
        return f'There was an error: {response}'
    # Check if there are matches on the query
    if len(response['results']) == 0:
        return 'No hay coincidencias'
    # Construct dataframe by searching all product results
    for i in range(response['paging']['primary_results'] // 50 + 1):
        url = f'https://api.mercadolibre.com/sites/{site_id}/search?q={query}&catalog_listing=true&offset={i*50}'
        resp = requests.get(url, headers=headers).json()
        # When the data reach one hundred columns stop, performance related
        if df.shape[0] >= 100:
            break
        for r in resp['results']:
            # Some products don't have catalog, ignore them
            if r['catalog_product_id'] == None:
                continue
            # Get all data
            url = f'https://api.mercadolibre.com/products/{r["catalog_product_id"]}'
            catalog_name = requests.get(url, headers=headers).json()['name']
            name = r['title']
            link = r['permalink']
            # Preparing the link in markdown format
            link = f'[{name}]({link})'
            price = r['price']
            url = f"https://api.mercadolibre.com/visits/items?ids={r['id']}"
            visits = requests.get(url, headers=headers).json()[r['id']]
            # Append to datafram
            df.loc[len(df), :] = [name, price, catalog_name, visits, link]
    
    # Ordenar por visitas
    df.sort_values('Visitas',ascending=False, inplace=True)        
    
    return html.Div([dash_table.DataTable(df.to_dict('records'), 
                                columns = [{"name": i, "id": i} if i != 'URL' else {"name": i, "id": i, 'presentation':'markdown'} for i in df.columns],
                               page_size =10, 
                               style_cell = {'overflow':'hidden', 'textOverflow':'ellipsis', 'maxWidth':10},
                               style_header={
                                    'backgroundColor': 'rgb(16, 40, 122)',
                                    'color': 'white'
                                },
                                style_data={
                                    'backgroundColor': 'rgb(90, 168, 225)',
                                    'color': 'white'
                                },
                                style_data_conditional=[{
                                    'if': {'column_id': 'URL'},
                                    'backgroundColor':'rgb(3, 14, 75)'
                                }],
                               tooltip_data=[
                                    {
                                        column: {'value': str(value), 'type': 'markdown'}
                                        for column, value in row.items()
                                    } for row in df.to_dict('records')
                                ],
                                tooltip_duration=None,
                               tooltip_header={i: i for i in df.columns},
                               css=[{
                                    'selector': '.dash-table-tooltip',
                                    'rule': 'background-color: rgb(43, 62, 167); font-family: monospace; color: white'
                                }],
                               export_format = 'xlsx')]
                   )
        
    
        