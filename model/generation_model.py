import pandas as pd


class GenerationModel:

    def __init__(self, wind_capacity_kw=5000):
        self.wind_capacity = wind_capacity_kw

        # wind curve parameters
        self.cut_in = 2
        self.rated = 12
        self.cut_out = 25

        # solar defaults
        self.performance_ratio = 0.85

    # wind curve
    def wind_power_curve(self, v):
        if v < self.cut_in or v > self.cut_out:
            return 0

        if v < self.rated:
            return self.wind_capacity * ((v - self.cut_in) / (self.rated - self.cut_in)) ** 3

        return self.wind_capacity

    # wind generation
    def compute_wind_generation(self, wind_df):
        power = wind_df["wind_speed"].apply(self.wind_power_curve)
        power.name = "wind_generation_kw"
        return power

    # solar model
    def solar_power(self, radiation, capacity_kw):
        power = (radiation / 1000) * capacity_kw * self.performance_ratio
        return power.clip(lower=0, upper=capacity_kw)

    # solar generation
    def compute_solar_generation(self, solar_df, capacity_kw=1000):
        power = self.solar_power(solar_df["radiation"], capacity_kw)
        power.name = "solar_generation_kw"
        return power