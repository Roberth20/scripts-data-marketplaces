from flask import Flask, request, redirect

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('dev.py')

@app.get('/authorize')
def authorize():
    url = f"https://auth.mercadolibre.com.cl/authorization?response_type=code&client_id={app.config['APP_ID']}&redirect_uri={app.config['REDIRECT_URI']}"
    print(url)
    return "test"

@app.route("/authentication")
def auth():
    print(request.args)

@app.get("/")
def inde():
    return "APP"

if __name__ == '__main__':
    app.run(port=5000)
