import requests
import oracledb
import pandas as pd

connection = oracledb.connect(
    user="ADMIN",
    password="Password1234",
    dsn="amazonsales_low",
    config_dir="/home/datascience/wallet",
    wallet_location="/home/datascience/wallet",
    wallet_password="Password1234"
)

def run_sql(query="SELECT * FROM AMAZON FETCH FIRST 10 ROWS ONLY"):
    df = pd.read_sql(query, connection)
    print(df.head())
