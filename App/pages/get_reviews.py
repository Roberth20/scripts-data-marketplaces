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
import os
import time

# Setting up the page of the app
dash.register_page(__name__, path="/mlc_reviews", name="Opiniones")

layout = html.Div([
    dbc.Row(dbc.Col(html.H2(children='Recoleccion de opiniones'), width=12), justify='center'),
    dbc.Row(dbc.Col(html.P('Seleccione una categoria y una tendencia para obtener las opiniones de los productos.'))),
    dcc.Interval(id="refresh-dropdowns", interval=10000),
    dbc.Row([
        dbc.Col(dcc.Dropdown(id='cats-reviews', placeholder="Escriba una categoria"), 
                width=5),
    ], justify="evenly"),
    dbc.Row(dbc.Col(
        dcc.Loading(id='charging-reviews',
                children=dcc.Graph(id = "table-revs")
                   ),
        style={'display':'none'},
        id = "container-rev")
    ),
    dbc.Row([
        dbc.Col(html.Div([
            html.Br(),
            html.P("Una vez cargada la previsualizacion de la tabla de datos, puede desacargar: "),
        ]),
               width='auto', align="end"),
        dbc.Col(dbc.Button("Descargar", id="save-revs", n_clicks=0), width=3),
        dbc.Col(dcc.Download(id='download-revs'))
    ], align='end')
])

@callback(Output("cats-reviews", 'options'),
         Input('refresh-dropdowns', 'n_intervals'))
def refresh_dropdown_category(n):
    # Auto-update the options to get reviews
    files = [(i, i[:-5]) for i in os.listdir("files") if i[-4:]=="xlsx"]
    cats = [f[1] for f in files]
    return cats


@callback(Output("table-revs", "figure"), Output('container-rev', 'style'),
         Input('cats-reviews', 'value'))
def search_revs(cat):
    # Check again if the category is on the files
    if not cat:
        raise PreventUpdate
    file = None
    files = [(i, i[:-5]) for i in os.listdir("files") if i[-4:]=="xlsx"]
    for f in files:
        if f[1] == cat:
            file = f[0]

    if not file:
        raise PreventUpdate

    # Load data
    data = pd.read_excel(f"files/{file}")
    
    with open('files/auth.json') as f:
        auth_data = json.load(f)
        token = auth_data["access_token"]
        
    headers = {
        'Authorization': f'Bearer {token}'
    }
    # Retrieve reviews from Mercado Libre
    reviews = []
    for iid in data['ID']:
        url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50'
        resp = requests.get(url, headers=headers)
        # To prevent Too many requests error, pause the program after each request
        time.sleep(0.5)
        try:
            resp = resp.json()
        except:
            print(resp.text)
            raise PreventUpdate
        try:
            rev = resp['reviews']
        except:
            print(resp)
            raise PreventUpdate
        if resp['paging']['total'] > 50:
            for i in range(resp['paging']['total']//50):
                url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50&offset={50*(i+1)}'
                resp2 = requests.get(url, headers=headers).json()
                time.sleep(0.5)
                try:
                    rev += resp2['reviews']
                except:
                    print(resp2)
                    raise PreventUpdate
        if len(rev) == 0:
            continue
        for r in rev:
            tmp = {}
            tmp['ID'] = r['id']
            tmp['Item'] = iid
            tmp['rate'] = r['rate']
            tmp['content'] = r['content']
            reviews.append(tmp)

    # Preparing a small table to show the reviews
    reviews = pd.DataFrame(reviews)
    sh_rev = reviews.iloc[:10, :]
    columns = [f"<b>{i}</b>" for i in reviews.columns]
    fig = go.Figure(go.Table(
        header = dict(values = columns,
                    fill_color = "#082275",
                    align = "center",
                    font = dict(color = "white"),
                    ),#height = 50),
        cells = dict(values=[sh_rev[item] for item in reviews.columns],
                    fill_color = "#0f83f7",
                    line_color = "white",
                    align = "center",
                    font = dict(color='white'))
        ))
    fig.update_layout(margin = dict(l=10, r=10, b=10, t=10, pad = 0),
                     plot_bgcolor='rgba(0, 0, 0, 0)',
                     paper_bgcolor='rgba(0,0,0,0)')
    reviews.to_json(f"files/{cat}-reviews.json")
    return fig, {'display':'block'}

@callback(Output('download-revs', 'data'), 
         Input('save-revs', 'n_clicks'), Input('cats-reviews', 'value'),
         prevent_initial_call=True)
def download_data_revs(n_clicks, cat):
    if n_clicks == 0:
        raise PreventUpdate
    if not cat:
        raise PreventUpdate
    if not os.path.exists(f"files/{cat}-reviews.json"):
        raise PreventUpdate
    data = pd.read_json(f"files/{cat}-reviews.json")
    return dcc.send_data_frame(data.to_excel, f"{cat}-reviews.xlsx")

