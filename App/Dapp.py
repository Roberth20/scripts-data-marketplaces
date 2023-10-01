from dash.exceptions import PreventUpdate
import requests
from dash import Dash
from flask import redirect, request
import json
from flask_apscheduler import APScheduler
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash

try:
    from instance import dev
    config = dev
except:
    from instance import test
    config = dev

dash_app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], use_pages=True)
server = dash_app.server
scheduler = APScheduler()

dash_app.layout = html.Div([
    html.H1("Aplicacion de exploracion de productos"),
    html.Div([
        html.Div(
            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
        ) for page in dash.page_registry.values()
    ]),
    dash.page_container    
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
    sever.run(debug=config.DEBUG)

    