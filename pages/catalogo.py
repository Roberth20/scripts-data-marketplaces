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
    # Request the product query with specific parameters for Mercado Libre Chile and with active products
    status = 'active'
    site_id = 'MLC'
    url = f'https://api.mercadolibre.com/products/search?status={status}&site_id={site_id}&q={query}&limit=10'
    response = requests.get(url, headers=headers).json()
    # Check for error messages
    if 'message' in response.keys():
        return f'There was an error: {response}'
    # Check if there are matches on the query
    if len(response['results']) == 0:
        return 'No hay coincidencias'
    # Construct dataframe
    data = pd.DataFrame(response['results'])
    # This particular case is when the results are parents, in this case the search query need
    # to be more specific
    if 'parent_id' not in data.columns:
        return "Busqueda poco especifica, no esposible encontrar resultados."
    # Clean data
    data.drop(['status', 'domain_id', 'settings', 'main_features', 'attributes', 
                'pictures', 'parent_id', 'children_ids', 'quality_type'], axis=1, inplace=True)
    df = []
    # Get catalog rivals and their info
    text = "Competencias de catalogo para los productos: "
    for i, row in data.iterrows():
        url = f'https://api.mercadolibre.com/products/{row["id"]}/items'
        response = requests.get(url, headers=headers).json()
        if 'error' in response.keys():
            continue
        df += response['results']
        text += row['name'] + ', '
    # Check if there is competition 
    if len(df) == 0:
        return f'No hay competencias de catalogo para productos de la busqueda: {query}'
    # Prepare DataFrame with rivals and clean
    df = pd.DataFrame(df)
    l = df.tags.to_list()
    l.sort()
    tags = pd.get_dummies(pd.DataFrame(l), prefix='tag')
    shipping = pd.DataFrame(df.shipping.to_list())
    l = []
    for address in df.seller_address.to_list():
        l.append({'seller_address_city':address['city']['name']})
    address = pd.DataFrame(l)
    df = pd.concat([df, tags, shipping, address], axis=1)
    df.drop(['shipping', 'tags', 'deal_ids', 'site_id', 
             'currency_id', 'inventory_id', 'sale_terms',
            'seller_address'], axis=1, inplace=True)
    df.rename(columns={'item_id':'item'}, inplace=True)
    names = []
    for id in df.item:
        url = f'https://api.mercadolibre.com/items/{id}'
        names.append(requests.get(url, headers=headers).json()['title'])
    df['item'] = names
    
    return html.Div([html.P(text), 
                     dash_table.DataTable(df.to_dict('records'), 
                                columns = [{"name": i, "id": i} for i in df.columns],
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
        
    
        