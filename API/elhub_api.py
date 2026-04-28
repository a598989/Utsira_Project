import pandas as pd
from api.base_api import BaseAPI


class ElhubAPI(BaseAPI):

    BASE_URL = "https://api.elhub.no/energy-data/v0"

    # consumption data
    def get_consumption(
        self,
        entity="grid-area",
        dataset="consumption_per_grid_area_hour",
        area="NO2",
    ):
        url = f"{self.BASE_URL}/{entity}"

        params = {
            "dataset": dataset,
            "gridArea": area,
        }

        data = self.get(url, params=params)

        records = []
        for item in data.get("data", []):
            records.append({
                "time": pd.to_datetime(item["startTime"]),
                "load": item["value"],
            })

        if not records:
            raise ValueError("No consumption data returned from Elhub API")

        df = pd.DataFrame(records)
        return df.set_index("time").sort_index()