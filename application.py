from dash.exceptions import PreventUpdate
import requests
from dash import Dash
from flask import redirect, request
import json
from flask_apscheduler import APScheduler
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash
from SQL.connection import conn
from SQL.models import Auth
from datetime import datetime
import pandas as pd
from sqlalchemy import insert

# Try to import the configuration to be used
try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = test

# Create the app and scheduler
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], use_pages=True)
application = app.server
scheduler = APScheduler()

# Defining basic layout
app.layout = html.Div([
    html.H1("Aplicacion de exploracion de productos"),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()]),
    html.Div(html.A("refresh", href="/refresh")),
    dash.page_container    
])

# Adding extras endpoints
@application.get('/authorize')
def authorize():
    # For this one, change .com.ar for the one of the country of Mercado Libre where the app was registered.
    # for example, The app registered in Chile will be .com.cl
    application.logger.info("Authorizing App")
    url = f"https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id={config.APP_ID}&redirect_uri={config.REDIRECT_URI}"
    return redirect(url)

@application.get("/authentication")
def auth():
    application.logger.info("Authenticating App")
    # Process the auth2 response from Mercado Libre
    code = request.args.get("code")
    if not code:
        application.logger.warning("There isn't authorization code with the request.")
        return "<h1>No authorization code</h1>"

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
        application.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    data = response.json()
    with conn.connect() as connection:
        stmt = (
            insert(Auth).
            values(access_token=data['access_token'], expires_in = datetime.now() + pd.Timedelta("6H"),
                  refresh_token=data['refresh_token'])
        )
        connection.execute(stmt)
        connection.commit()    
    return "<h1>Token saved</h1>"

@scheduler.task('interval', id='refresh_token', hours=4)
def refresh_token():
    application.logger.info("Updating programed token")
    with conn.connect() as con:
        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = json.dumps({
        'grant_type':'refresh_token',
        'client_id': config.APP_ID,
        'client_secret': config.CLIENT_SECRET,
        'refresh_token':auth['refresh_token']
    })
    response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=data)
    if not response:
        application.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    data = response.json()
    with conn.connect() as connection:
        stmt = (
            insert(Auth).
            values(access_token=data['access_token'], expires_in = datetime.now() + pd.Timedelta("6H"),
                  refresh_token=data['refresh_token'])
        )
        connection.execute(stmt)
        connection.commit()   

@application.get("/refresh")
def refresh_token2():
    application.logger.info("Refreshing token")
    with conn.connect() as con:
        auth = pd.read_sql("SELECT * FROM Autenticacion", con).iloc[-1, :]

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = json.dumps({
        'grant_type':'refresh_token',
        'client_id': config.APP_ID,
        'client_secret': config.CLIENT_SECRET,
        'refresh_token':auth['refresh_token']
    })
    response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=data)
    if not response:
        application.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    data = response.json()
    with conn.connect() as connection:
        stmt = (
            insert(Auth).
            values(access_token=data['access_token'], expires_in = datetime.now() + pd.Timedelta("6H"),
                  refresh_token=data['refresh_token'])
        )
        connection.execute(stmt)
        connection.commit()   
    return "<h1>Token saved</h1>"

if __name__ == '__main__':
    scheduler.init_app(application)
    scheduler.start()
    application.run(debug=config.DEBUG, port=config.PORT)

    