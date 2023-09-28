from dash import Dash, html, dcc, Input, Output, callback
import pandas as pd
from dash.exceptions import PreventUpdate
import requests
import dash_bootstrap_components as dbc
from funcs import callbacks
from flask import redirect, request
import json
from flask_apscheduler import APScheduler

try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = dev

dash_app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = dash_app.server
scheduler = APScheduler()

dash_app.layout = html.Div([
    html.H1(children='Aplicacion de exploracion', className='header-title'),
    html.Br(),
    dcc.Dropdown(callbacks.cats.Name, id='cat-selection', placeholder="Escriba para buscar una categoria"),
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

@server.get('/authorize')
def authorize():
    url = f"https://auth.mercadolibre.com.cl/authorization?response_type=code&client_id={config.APP_ID}&redirect_uri={config.REDIRECT_URI}"
    return redirect(url)

@server.get("/authentication")
def auth():
    code = request.args.get("code")
    if not code:
        return "No authorization code"

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }

    data = json.dumps({
        'grant_type': 'authorization_code',
        'client_id': config.APP_ID,
        'client_secret': config.CLIENT_SECRET,
        'code': code,
        'redirect_uri': config.REDIRECT_URI,
    })

    response = requests.post("https://api.mercadolibre.com/oauth/token", headers=headers, data=data)
    if not response:
        return "Hubo un error"
    with open("files/auth.json", 'w') as f:
        json.dump(response.json())
    return "Token saved"

@scheduler.task('interval', id='refresh_token', hours=4)
def refresh_token():
    with open('files/auth.json') as f:
        auth_data = json.load(f)

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = json.dumps({
        'grant_type':'refresh_token',
        'client_id': config.APP_ID,
        'client_secret': config.CLIENT_SECRET,
        'refresh_token':auth_data['refresh_token']
    })
    response = requests.post('https://api.mercadolibre.com/oauth/token', headrs=headers, data=data)
    print(response.text)

if __name__ == '__main__':
    scheduler.init_app(server)
    scheduler.start()
    dash_app.run(debug=config.DEBUG)

    