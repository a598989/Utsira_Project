import numpy as np


class GenerationModel:
    """
    Converts weather data into power generation.
    """

    def wind_power(self, wind_speed, capacity_kw=5000):
        """
        More realistic wind turbine curve
        """

        cut_in = 3
        rated = 12
        cut_out = 25

        power = np.zeros_like(wind_speed)

        # ramp-up region
        mask = (wind_speed >= cut_in) & (wind_speed <= rated)
        power[mask] = ((wind_speed[mask] - cut_in) / (rated - cut_in))**3

        # rated region
        mask = (wind_speed > rated) & (wind_speed <= cut_out)
        power[mask] = 1.0

        return power * capacity_kw

    def solar_power(self, radiation, capacity_kw=1000):
        """
        Convert W/m² → kW output
        """
        return (radiation / 1000) * capacity_kw