import pandas as pd
from api.base_api import BaseAPI


class OpenMeteoAPI(BaseAPI):

    # Fetches historical solar radiation data from Open-Meteo.
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def get_solar_radiation(
        self,
        latitude=59.305,
        longitude=4.886,
        start="2023-01-01",
        end="2023-12-31",
        timezone="Europe/Oslo",
    ):
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start,
            "end_date": end,
            "hourly": "shortwave_radiation",
            "timezone": timezone,
        }

        data = self.get(self.BASE_URL, params=params)

        df = pd.DataFrame({
            "time": data["hourly"]["time"],
            "radiation": data["hourly"]["shortwave_radiation"],
        })

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()

        return df