import numpy as np
import pandas as pd


class LoadModel:
    """
    Creates a realistic hourly electricity demand profile for Utsira.
    Includes:
    - 1 MW data center
    - residential demand
    - industry
    - water/wastewater
    - EV charging
    """

    def __init__(
        self,
        data_center_kw=1000,
        households=90,
        household_annual_kwh=15000,
        industry_kw=150,
        water_kw=40,
        ev_ports=200,
        ev_charger_kw=7.4,
        ev_simultaneous_fraction=0.25,
    ):
        self.data_center_kw = data_center_kw
        self.households = households
        self.household_annual_kwh = household_annual_kwh
        self.industry_kw = industry_kw
        self.water_kw = water_kw
        self.ev_ports = ev_ports
        self.ev_charger_kw = ev_charger_kw
        self.ev_simultaneous_fraction = ev_simultaneous_fraction

    def generate_load(self, index):
        hours = index.hour
        months = index.month

        data_center = pd.Series(self.data_center_kw, index=index)

        # Residential load: higher in winter, morning/evening peaks
        seasonal = 1.0 + 0.45 * np.cos(2 * np.pi * (months - 1) / 12)
        morning_peak = np.exp(-0.5 * ((hours - 7) / 2.0) ** 2)
        evening_peak = np.exp(-0.5 * ((hours - 19) / 2.5) ** 2)

        residential_shape = 0.6 + 0.25 * morning_peak + 0.45 * evening_peak
        residential_raw = seasonal * residential_shape

        annual_residential_kwh = self.households * self.household_annual_kwh
        residential = pd.Series(residential_raw, index=index)
        residential = residential * (annual_residential_kwh / residential.sum())

        # Industry and water
        industry = pd.Series(self.industry_kw, index=index)
        water = pd.Series(self.water_kw, index=index)

        # EV charging: mainly evening charging
        ev_peak_power = self.ev_ports * self.ev_charger_kw * self.ev_simultaneous_fraction
        ev_shape = np.exp(-0.5 * ((hours - 20) / 2.0) ** 2)
        ev = pd.Series(ev_peak_power * ev_shape, index=index)

        total_load = data_center + residential + industry + water + ev
        total_load.name = "total_load_kw"

        return pd.DataFrame({
            "data_center_kw": data_center,
            "residential_kw": residential,
            "industry_kw": industry,
            "water_kw": water,
            "ev_kw": ev,
            "total_load_kw": total_load
        })