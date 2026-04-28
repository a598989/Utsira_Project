import os
import requests
import pandas as pd


class FrostAPI:

    BASE_URL = "https://frost.met.no/observations/v0.jsonld"

    def __init__(self):
        self.client_id = os.getenv("FROST_CLIENT_ID")

        if not self.client_id:
            raise ValueError("FROST_CLIENT_ID not found in environment")

    # wind data
    def get_wind_data(self, station_id, start, end):
        params = {
            "sources": station_id,
            "elements": "wind_speed",
            "referencetime": f"{start}/{end}",
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            auth=(self.client_id, "")
        )
        response.raise_for_status()

        data = response.json().get("data", [])

        records = []
        for item in data:
            time = item["referenceTime"]
            value = item["observations"][0]["value"]

            records.append({
                "time": pd.to_datetime(time),
                "wind_speed": value
            })

        df = pd.DataFrame(records)
        return df.set_index("time").sort_index()