from API.base_api import BaseAPI
import pandas as pd


class OpenMeteoAPI(BaseAPI):
    """
    Fetch solar radiation data (free, no auth required).
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def get_solar_radiation(self,
                             lat=59.3,
                             lon=4.9):

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "shortwave_radiation",
            "timezone": "UTC"
        }

        data = self.get(self.BASE_URL, params=params)

        df = pd.DataFrame({
            "time": data["hourly"]["time"],
            "radiation": data["hourly"]["shortwave_radiation"]
        })

        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

        return df