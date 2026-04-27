from API.base_api import BaseAPI
import pandas as pd


class ElhubAPI(BaseAPI):
    """
    Elhub Energy Data API (NO AUTH REQUIRED for public datasets)
    """

    BASE_URL = "https://api.elhub.no/energy-data/v0"

    def get_consumption(self,
                        entity="grid-area",
                        dataset="consumption_per_grid_area_hour",
                        area="NO2"):

        """
        Fetch hourly consumption for a Norwegian price/grid area.

        Example:
        NO2 = Southwest Norway (closest to Utsira)
        """

        url = f"{self.BASE_URL}/{entity}"

        params = {
            "dataset": dataset,
            "gridArea": area
        }

        data = self.get(url, params=params)

        records = []

        for item in data["data"]:
            records.append({
                "time": item["startTime"],
                "load": item["value"]
            })

        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")

        return df