import dash
from dash.exceptions import PreventUpdate
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup as bs
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc
from dash import html
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/mlc_products", name="Datos de productos", prevent_initial_callbacks=True)
cats = pd.read_json("files/cats_mlc.json")

layout = html.Div([
    html.H2(children='Recoleccion de datos de productos'),
    html.Br(),
    dcc.Dropdown(cats.Name, id='cat-selection', placeholder="Escriba para buscar una categoria"),
    html.Br(),
    dcc.Dropdown(id="trends", placeholder='Seleccione tendencia para explorar'),
    dcc.Store(id="trends-data"),
    dcc.Store(id='category'),
    html.Br(),
    html.Div([
        html.Div(html.P('Para descargar el excel con los datos completos de la muestra: '), 
                 style={'display':'inline-block', 'margin-left':'10px', 'width':'35%', 
                       'margin-top':'10px'}),
        html.Div(dbc.Button("Descargar", id="save-data", n_clicks=0), 
                 style={'display':'inline-block'}),
        dcc.Download(id='download-data')
    ], style={'display':'flex'}),
    dcc.Loading(id='charging-products',
                children=html.Div(dcc.Graph(id = "table"),
                                  id='container',
                                 style={'display':'none'})),
])

@callback(Output('trends', 'options'), Output('trends-data', 'data'), 
          Output('category', 'data'),
          Input('cat-selection', 'value'))
def search_cat(value):
    if value == None:
        raise PreventUpdate
    id = cats.loc[cats['Name'] == value, 'ID'].values[0]
    with open('files/auth.json') as f:
        auth_data = json.load(f)
        token = auth_data["access_token"]
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.mercadolibre.com/trends/MLC/{id}'
    result = requests.get(url, headers=headers)
    try:
        result = result.json()
    except:
        print(result)
        raise PreventUpdate
    if type(result) != list:
        print(result)
        raise PreventUpdate
        
    trends = pd.DataFrame(result)
    if trends.shape[0] > 20:
        trends = trends.iloc[:20, :]
    return trends['keyword'], trends.to_json(), json.dumps({'category':value})

@callback(Output('table', 'figure'), Output('container', 'style'), 
          Input('trends-data', 'data'), Input('trends', 'value'), Input('category', 'data'))
def search_products(json_data, trend, json_cat):
    if not json_data or not trend:
        raise PreventUpdate

    with open('files/auth.json') as f:
        auth_data = json.load(f)
        token = auth_data["access_token"]
        
    headers = {
        'Authorization': f'Bearer {token}'
    }
    category = json.loads(json_cat)
    trends = pd.read_json(json_data)
    prueba = []
    tendencia = trends.loc[trends['keyword'] == trend, :]
    count = 0
    data = requests.get(tendencia["url"].values[0]).text
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
                raise PreventUpdate
            try:
                tmp = {}
                tmp['ID'] = test['id']
                tmp["Nombre"] = test['title']
                tmp['seller_id'] = test['seller_id']
                tmp['Precio'] = test['price']
                tmp["keyword"] = tendencia['keyword']
                prueba.append(tmp)
                count += 1
            except:
                if test["error"] == 'resource not found':
                    print(tag)
                    raise PreventUpdate
                else:
                    print(test)
                    raise PreventUpdate
            if count == 20:
                break
    data = pd.DataFrame(prueba)
    columns = [f"<b>{i}</b>" for i in data.columns]
    fig = go.Figure(go.Table(
        header = dict(values = columns,
                    fill_color = "#082275",
                    align = "center",
                    font = dict(color = "white"),
                    ),#height = 50),
        cells = dict(values=[data[item] for item in data.columns],
                    fill_color = "#0f83f7",
                    line_color = "white",
                    align = "center",
                    font = dict(color='white'))
        ))
    fig.update_layout(margin = dict(l=10, r=10, b=10, t=10, pad = 0),
                     plot_bgcolor='rgba(0, 0, 0, 0)',
                     paper_bgcolor='rgba(0,0,0,0)')
    data.to_excel(f"files/{category['category']} @ {trend}.xlsx", index=False)
    return fig, {'display':'block'}

@callback(Output('download-data', 'data'), 
         Input('save-data', 'n_clicks'), Input('trends', 'value'), Input('category', 'data'),
         prevent_initial_call=True)
def download_data(n_clicks, trend, cat):
    if n_clicks == 0:
        raise PreventUpdate
    if not cat:
        raise PreventUpdate
    if not os.path.exists(f"files/{json.loads(cat)['category']}-{trend}.xlsx"):
        raise PreventUpdate
    data = pd.read_excel(f"files/{json.loads(cat)['category']}-{trend}.xlsx")
    return dcc.send_data_frame(data.to_excel, f"{json.loads(cat)['category']} @ {trend}.xlsx")
