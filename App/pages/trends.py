import dash
from dash.exceptions import PreventUpdate
import pandas as pd
from dash import Input, Output, callback, dcc
from dash import html
import dash_bootstrap_components as dbc
from SQL.connection import conn
from SQL.models import Trends
import sqlalchemy as db

# Setting up the pages
dash.register_page(__name__, path="/trends", name="Tendencias", prevent_initial_callbacks=True)

layout = html.Div([
    dbc.Row(dbc.Col(html.H2(children='Tendencias'), width=12), justify='center'),
    dbc.Row([
        dbc.Col(html.Div([
            html.Br(),
            html.P("Aqui puede descargar la informacion historica de las tendencias almacenadas en la base de datos"),
        ]),
               width='auto', align="end"),
        dbc.Col(html.Div([
                dbc.Button("Descargar", id="save-trends", n_clicks=0),
                dcc.Download(id='download-trends')])
               )
    ], align='end')
])

@callback(Output('download-trends', 'data'), 
         Input('save-trends', 'n_clicks'),
         prevent_initial_call=True)
def download_data_revs(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate
    with conn.connect() as con:
        stmt = (db.select(Trends))
        trends = pd.read_sql(stmt, con)
    return dcc.send_data_frame(trends.to_excel, f"Tendencias.xlsx")