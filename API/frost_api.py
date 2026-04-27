from API.base_api import BaseAPI
import pandas as pd


class FrostAPI(BaseAPI):
    """
    Fetches meteorological data from MET Norway Frost API.
    """

    BASE_URL = "https://frost.met.no/observations/v0.jsonld"

    def __init__(self, client_id):
        super().__init__()
        self.client_id = client_id

    def get_wind_speed(self,
                       station="SN44560",   # Haugesund / near Utsira
                       start="2023-01-01",
                       end="2023-12-31"):

        params = {
            "sources": station,
            "elements": "wind_speed",
            "referencetime": f"{start}/{end}"
        }

        response = self.session.get(
            self.BASE_URL,
            params=params,
            auth=(self.client_id, "")
        )

        response.raise_for_status()
        data = response.json()

        records = []

        for item in data["data"]:
            records.append({
                "time": item["referenceTime"],
                "wind_speed": item["observations"][0]["value"]
            })

        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

        return df