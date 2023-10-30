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
from SQL.connection import conn
from sqlalchemy.orm import Session
from SQL.models import TrendingItems
from datetime import date

# Setting up the pages
dash.register_page(__name__, path="/mlc_products", name="Datos de productos", prevent_initial_callbacks=True)
with conn.connect() as con:
    cats = pd.read_sql("SELECT * FROM Categorias", con)

layout = html.Div([
    html.H2(children='Recoleccion de datos de productos'),
    html.Br(),
    html.Div([html.Div(dcc.Dropdown(cats['name'], id='cat-selection', placeholder="Escriba para buscar una categoria"),
                      style={"display":"inline-block", "width":"49%"}),
             html.Div(dcc.DatePickerRange(id="dates-range", start_date_placeholder_text="Start Period",
                                end_date_placeholder_text="End Period", calendar_orientation='vertical'),
                     style={"display":"inline-block", "verticalAlign":"top", "margin-left":"1em"})]),
    html.Br(),
    dcc.Loading(id='charging-products',
                children=html.Div(id='message-products',
                                 style={'display':'none'})),
    html.Div([
        html.Div(html.P('Para descargar el excel con los datos completos de la muestra: '), 
                 style={'display':'inline-block', 'margin-left':'10px', 'width':'35%', 
                       'margin-top':'10px'}),
        html.Div(dbc.Button("Descargar", id="save-data", n_clicks=0), 
                 style={'display':'inline-block'}),
        dcc.Download(id='download-data')
    ], style={'display':'flex'}),
    html.Div(dbc.Button('Cargar muestra', id='show-products', n_clicks=0),
            style={'display':'flex', 'margin-left':'5em'}),
    html.Div(dcc.Graph(id = "table"),
            id='container',
            style={'display':'none'}),
])

@callback(Output('message-products', 'children'), Output('message-products', 'style'),
          Input('cat-selection', 'value'), Input("dates-range", "start_date"),
         Input("dates-range", "end_date"))
def search_products(value, start, end):
    if value == None or start == None or end == None:
        raise PreventUpdate
    start_date = pd.to_datetime(start).date()
    end_date = pd.to_datetime(end).date()
    if (end_date - start_date).days > 150:
        message = html.P('Hubo un error. El rango de fecha seleccionado no puede ser mayor a 150 dias')
        return message, {'display':'block'}

    id = cats.loc[cats['name'] == value, 'id'].values[0]

    with conn.connect() as con:
        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]
        token = auth["access_token"]
        
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.mercadolibre.com/trends/MLC/{id}'
    result = requests.get(url, headers=headers)
    try:
        result = result.json()
    except:
        message = html.P(f"Hubo un error: {result}")
        return message, {'display':'block'}
    if type(result) != list:
        message = html.P(f"Hubo un error: {result}")
        return message, {'display':'block'}
        
    trends = pd.DataFrame(result)
    if trends.shape[0] > 20:
        trends = trends.iloc[:20, :]
        
    major_data = []
    text = ""
    for i, row in trends.iterrows():
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
                try:
                    test = response.json()
                except:
                    message = html.P(f'Hubo un error por: {response.text}')
                    return message, {'display':'block'}
                if 'error' in test.keys():
                    message = html.P(f'Hubo un error por: {test["error"]}, {tag}')
                    return message, {'display':'block'}
                    
                tmp = {}
                tmp['ID'] = test['id']
                tmp["Nombre"] = test['title']
                tmp['seller_id'] = test['seller_id']
                tmp['Precio'] = test['price']
                tmp["keyword"] = row['keyword']
                try:
                    tmp["Cantidad de ventas"] = test['sold_quantity']
                except:
                    text += f"Sin registro de ventas: {test['id']}."
                    tmp['Cantidad de ventas'] = 0
                try:
                    tmp['Fecha de publicacion'] = test['start_time']
                except:
                    text += f'Sin fecha de publicacion, cambiando por fecha de creacion para producto {test["id"]}'
                    tmp['Fecha de publicacion'] = test['date_created']
                urlv = f"https://api.mercadolibre.com/items/visits?ids={id}&date_from={start_date}&date_to={end_date}"
                try:
                    r = requests.get(urlv, headers=headers).json()
                    tmp['visitas'] = r[0]['total_visits']
                except:
                    text += f"Hubo un error con las visitas: {r}. Igualando a cero."
                    tmp['visitas'] = 0
                tmp['Calidad'] = test['health']
                prueba.append(tmp)
                count += 1

                if count == 20:
                    break
        major_data.append(pd.DataFrame(prueba))

    major_data = pd.concat(major_data, ignore_index=True)
    major_data.columns = ["item_id", "name", "seller_id", "price", "keyword", "items_sold", "publication_date", 
                         "visits", "quality"]
    major_data['category'] = value
    major_data['publication_date'] = pd.to_datetime(major_data['publication_date']).dt.date
    major_data.fillna(0, inplace=True)
    trends['category'] = value
    trends['date'] = date.today()
    trends.drop("url", axis=1, inplace=True)
    trends.columns = ['keywords', 'category', 'date']

    with conn.connect() as con:
        major_data.to_sql("ProductosYTendencias", con, index=False, if_exists='append')
        trends.to_sql('Tendencias', con, index=False, if_exists='append')
        con.commit()
        text += "Cargado exitosamente a la base de datos."

    return html.P(text), {'display':'block'}

@callback(Output('table', 'figure'), Output('container', 'style'), 
          Input('cat-selection', 'value'), Input('show-products', 'n_clicks'),
         suppress_callback_exceptions=True)
def show_products(value, n):
    if value == None or n == 0:
        raise PreventUpdate  

    with conn.connect() as con:
        major_data = pd.read_sql(f"SELECT * FROM ProductosYTendencias WHERE category = '{value}'", con)
    
    columns = [f"<b>{i}</b>" for i in major_data.columns]
    sample = major_data.iloc[::5, :]
    fig = go.Figure(go.Table(
        header = dict(values = columns,
                    fill_color = "#082275",
                    align = "center",
                    font = dict(color = "white"),
                    ),#height = 50),
        cells = dict(values=[sample[item] for item in sample.columns],
                    fill_color = "#0f83f7",
                    line_color = "white",
                    align = "center",
                    font = dict(color='white'))
        ))
    fig.update_layout(margin = dict(l=10, r=10, b=10, t=10, pad = 0),
                     plot_bgcolor='rgba(0, 0, 0, 0)',
                     paper_bgcolor='rgba(0,0,0,0)')

    return fig, {'display':'block'}

@callback(Output('download-data', 'data'), 
         Input('save-data', 'n_clicks'), Input('cat-selection', 'value'),
         prevent_initial_call=True)
def download_data(n_clicks, cat):
    if n_clicks == 0:
        raise PreventUpdate
    if not cat:
        raise PreventUpdate
    with conn.connect() as con:
        data = pd.read_sql(f"SELECT * FROM ProductosYTendencias WHERE category = '{cat}'", con)
    return dcc.send_data_frame(data.to_excel, f"{cat}.xlsx")
