from dash.exceptions import PreventUpdate
import requests
from dash import Dash
from flask import redirect, request
import json
from flask_apscheduler import APScheduler
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash

# Try to import the configuration to be used
try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = test

# Create the app and scheduler
dash_app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], use_pages=True)
server = dash_app.server
scheduler = APScheduler()

# Defining basic layout
dash_app.layout = html.Div([
    html.H1("Aplicacion de exploracion de productos"),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    dash.page_container    
])

# Adding extras endpoints
@server.get('/authorize')
def authorize():
    # For this one, change .com.ar for the one of the country of Mercado Libre where the app was registered.
    # for example, The app registered in Chile will be .com.cl
    server.logger.info("Authorizing App")
    url = f"https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id={config.APP_ID}&redirect_uri={config.REDIRECT_URI}"
    return redirect(url)

@server.get("/authentication")
def auth():
    server.logger.info("Authenticating App")
    # Process the auth2 response from Mercado Libre
    code = request.args.get("code")
    if not code:
        server.logger.warning("There isn't authorization code with the request.")
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
        server.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    with open("files/auth.json", 'w') as f:
        json.dump(response.json())
    return "<h1>Token saved</h1>"

@scheduler.task('interval', id='refresh_token', hours=4)
def refresh_token():
    server.logger.info("Updating programed token")
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
    response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=data)
    if not response:
        server.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    with open("files/auth.json", 'w') as f:
        json.dump(response.json(), f)

@server.get("/refresh")
def refresh_token2():
    server.logger.info("Refreshing token")
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
    response = requests.post('https://api.mercadolibre.com/oauth/token', headers=headers, data=data)
    if not response:
        server.logger.error("The was an error retrieving the token.")
        return "<h1>Hubo un error</h1>"
    with open("files/auth.json", 'w') as f:
        json.dump(response.json(), f)
    return "<h1>Token saved</h1>"

if __name__ == '__main__':
    scheduler.init_app(server)
    scheduler.start()
    dash_app.run(debug=config.DEBUG)

    