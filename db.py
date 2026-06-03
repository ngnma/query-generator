import requests
import oracledb
import pandas as pd

connection = oracledb.connect(
    user="ADMIN",
    password="YOUR_DATABASE_PASSWORD",
    dsn="YOURDB_low",
    config_dir="/home/datascience/wallet",
    wallet_location="/home/datascience/wallet",
    wallet_password="YOUR_WALLET_PASSWORD"
)

def run_sql(query="SELECT * FROM AMAZON FETCH FIRST 10 ROWS ONLY"):
    df = pd.read_sql(query, connection)
    print(df.head())
