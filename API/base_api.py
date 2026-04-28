import requests
import pandas as pd


class BaseAPI:

    def __init__(self):
        self.session = requests.Session()

    def get(self, url, params=None):
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def to_dataframe(self, records, time_key, value_key):
        df = pd.DataFrame(records)
        df[time_key] = pd.to_datetime(df[time_key])
        df = df.set_index(time_key)
        return df[[value_key]]