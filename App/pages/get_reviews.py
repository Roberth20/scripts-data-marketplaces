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
from SQL.connection import conn
from SQL.models import Reviews, TrendingItems
import sqlalchemy as db

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
    dbc.Row(dbc.Col(html.Br())),
    dbc.Row(dbc.Col(
        dcc.Loading(id='charging-reviews',
                children=html.Div([html.Br(), dcc.Graph(id = "table-revs")],
                                  style={'display':'none'},
                                  id = "container-rev")
                   )
        )
    ),
    dbc.Row([
        dbc.Col(html.Div([
            html.Br(),
            html.P("Una vez cargada la previsualizacion de la tabla de datos, puede descargar: "),
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
    with conn.connect() as con:
        cats = pd.read_sql(f"SELECT UNIQUE(category) FROM ProductosYTendencias", con)
    return cats['category'].values


@callback(Output("table-revs", "figure"), Output('container-rev', 'style'),
         Input('cats-reviews', 'value'))
def search_revs(cat):
    # Check again if the category is on the files
    if not cat:
        raise PreventUpdate

    # Load data
    with conn.connect() as con:
        data = pd.read_sql(f"SELECT * FROM ProductosYTendencias WHERE category='{cat}'", con)
        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]
        token = auth["access_token"]
        
    headers = {
        'Authorization': f'Bearer {token}'
    }
    # Retrieve reviews from Mercado Libre
    reviews = []
    for iid in data['item_id']:
        url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50'
        resp = requests.get(url, headers=headers)
        # To prevent Too many requests error, pause the program after each request
        time.sleep(0.5)
        try:
            resp = resp.json()
        except:
            print("Error obteniendo datos del item: ", resp.text)
            raise PreventUpdate
        try:
            rev = resp['reviews']
        except:
            print("Error obteniendo datos del item: ", resp)
            raise PreventUpdate
        if resp['paging']['total'] > 50:
            err = False
            for i in range(resp['paging']['total']//50):
                url = f'https://api.mercadolibre.com/reviews/item/{iid}?limit=50&offset={50*(i+1)}'
                resp2 = requests.get(url, headers=headers).json()
                time.sleep(0.5)
                try:
                    rev += resp2['reviews']
                except:
                    if not err:
                        print("Error obteniendo datos de opiniones: ", resp2)
                        err = True
                pass
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
    with conn.connect() as con:
        stmt = (db.select(Reviews)
            .where(Reviews.item_id == TrendingItems.item_id)
            .where(TrendingItems.category == cat))
        revs = pd.read_sql(stmt, con)
        reviews.columns = ['id', 'item_id', 'rate', 'content']
        reviews.fillna(0, inplace=True)
        diff = reviews[~reviews['id'].astype('str').isin(revs['id'])].copy()
        diff.drop_duplicates(inplace=True)
        if diff.shape[0] > 0:
            print("Hay datos nuevos")  
            diff.to_sql("Opiniones", con, if_exists="append", index=False)
            con.commit()
        else:
            print("Nada nuevo")
    return fig, {'display':'block'}

@callback(Output('download-revs', 'data'), 
         Input('save-revs', 'n_clicks'), Input('cats-reviews', 'value'),
         prevent_initial_call=True)
def download_data_revs(n_clicks, cat):
    if n_clicks == 0:
        raise PreventUpdate
    if not cat:
        raise PreventUpdate
    with conn.connect() as con:
        stmt = (db.select(Reviews)
                .where(Reviews.item_id == TrendingItems.item_id)
                .where(TrendingItems.category == cat))
        revs = pd.read_sql(stmt, con)
    return dcc.send_data_frame(revs.to_excel, f"{cat}-reviews.xlsx")

