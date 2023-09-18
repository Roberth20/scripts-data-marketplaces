from flask import Flask, request, redirect

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('dev.py')

@app.get('/authorize')
def authorize():
    url = f"https://auth.mercadolibre.com.cl/authorization?response_type=code&client_id={app.config['APP_ID']}&redirect_uri={app.config['REDIRECT_URI']}"
    redirect(url)

@app.get("/authentication")
def auth():
    try:
        code = request.args.get("code")
    except:
        return "No authorization code"

    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }

    data = json.dumps({
        'grant_type': 'authorization_code',
        'client_id': app.config['APP_ID'],
        'client_secret': app.config['CLIENT_SECRET'],
        'code': code,
        'redirect_uri': app.config['REDIRECT_URI'],
    })

    response = requests.post("https://api.mercadolibre.com/oauth/token", headers=headers, data=data)
    return response.json()

@app.get("/")
def inde():
    return "APP"

if __name__ == '__main__':
    app.run(port=5000)
