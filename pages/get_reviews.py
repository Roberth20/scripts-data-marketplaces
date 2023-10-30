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
                children=html.Div(id="message-reviews", style={'display':'none'})
                   )
        )
    ),
    dbc.Row(dbc.Col(dbc.Button('Cargar muestra', id='show-revs', n_clicks=0), width=10), justify='center'),
    dbc.Row(dbc.Col(html.Div([html.Br(), dcc.Graph(id = "table-revs")],
                                  style={'display':'none'},
                                  id = "container-rev"))),
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

@callback(Output('message-reviews', 'children'), Output('message-reviews', 'style'),
         Input('cats-reviews', 'value'))
def search_revs(cat):
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
    text = ""
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
            message = html.P(f"Error obteniendo datos del item: {resp.text}")
            return message, {'display':'block'}
        try:
            rev = resp['reviews']
        except:
            message = html.P(f"Error obteniendo datos del item: {resp}")
            return message, {'display':'block'}
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
                        text = f"Error obteniendo datos de opiniones: {resp2}"
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

    reviews = pd.DataFrame(reviews)
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
            diff.to_sql("Opiniones", con, if_exists="append", index=False)
            con.commit()
            text += "Datos cargados con exito a la base de datos"
        else:
            text += "Proceso completado, pero no hay datos nuevos para cargar."

    return html.P(text), {'display':'block'}


@callback(Output("table-revs", "figure"), Output('container-rev', 'style'),
         Input('cats-reviews', 'value'), Input('show-revs', 'n_clicks'))
def show_revs(cat, n):
    if not cat or n == 0:
        raise PreventUpdate        

    with conn.connect() as con:
        stmt = (db.select(Reviews)
                .where(Reviews.item_id == TrendingItems.item_id)
                .where(TrendingItems.category == cat))
        reviews = pd.read_sql(stmt, con)
    
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

