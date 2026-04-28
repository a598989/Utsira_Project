import pandas as pd

from api.frost_api import FrostAPI
from api.openmeteo_api import OpenMeteoAPI
from model.generation_model import GenerationModel
from model.load_model import LoadModel
from model.battery_model import BatteryModel
from utils.kpi_export import export_kpis

from utils.plotting import (
    plot_wind_power,
    plot_solar_power,
    plot_total_generation,
    plot_generation_stack,
    plot_week,
    plot_monthly,
    plot_battery_power_full,
    plot_system_balance,
    plot_unmet_load,
    plot_load_distribution,
    plot_battery_power,
    plot_curtailment,
    plot_net_balance,
    plot_dunkelflaute,
    plot_district_heating,
)

# config
YEAR = 2023

WIND_CAPACITY = 5000
WIND_BASELINE = 5.5
SOLAR_CAPACITY = 1000

BATTERY_CAPACITY = 130000     
BATTERY_POWER = 5000
BATTERY_EFFICIENCY = 0.92
INITIAL_SOC = 0.80

LAT = 59.305
LON = 4.886
STATION_ID = "SN39040"

WINTER_WEEK = "2023-01-15"
SUMMER_WEEK = "2023-07-15"
DUNKEL_START = "2023-01-15"

STARTUP_CUT = f"{YEAR}-01-05"

# init
frost = FrostAPI()
openmeteo = OpenMeteoAPI()
gen_model = GenerationModel(wind_capacity_kw=WIND_CAPACITY)

# wind
wind_df = frost.get_wind_data(
    station_id=STATION_ID,
    start=f"{YEAR}-01-01T00:00:00Z",
    end=f"{YEAR}-12-31T23:00:00Z",
)

wind_df = wind_df.resample("1h").mean().interpolate()
wind_df["wind_speed"] = (
    wind_df["wind_speed"]
    .rolling(48, center=True)
    .mean()
    .bfill()
    .ffill()
)
wind_df["wind_speed"] += WIND_BASELINE

wind_power = gen_model.compute_wind_generation(wind_df)
wind_power = wind_power.rolling(12).mean().bfill().ffill()

# solar
solar_df = openmeteo.get_solar_radiation(
    latitude=LAT,
    longitude=LON,
    start=f"{YEAR}-01-01",
    end=f"{YEAR}-12-31",
)

solar_df = solar_df.resample("1h").mean().interpolate()

solar_power = gen_model.compute_solar_generation(
    solar_df,
    capacity_kw=SOLAR_CAPACITY,
).bfill().ffill()

# align
wind_power = wind_power.tz_localize(None)
solar_power = solar_power.tz_localize(None)

common_index = wind_power.index.intersection(solar_power.index)

wind_power = wind_power.loc[common_index]
solar_power = solar_power.loc[common_index]

total_generation = wind_power + solar_power

# generation plots
plot_wind_power(wind_power)
plot_solar_power(solar_power)
plot_total_generation(wind_power, solar_power)

plot_generation_stack(wind_power, solar_power)
plot_week(wind_power, solar_power, WINTER_WEEK)
plot_week(wind_power, solar_power, SUMMER_WEEK)
plot_monthly(wind_power, solar_power)

# load
load_model = LoadModel()
load_df = load_model.generate_load(common_index)

# battery
battery = BatteryModel(
    capacity_kwh=BATTERY_CAPACITY,
    power_kw=BATTERY_POWER,
    efficiency=BATTERY_EFFICIENCY,
    initial_soc_fraction=INITIAL_SOC,
)

battery_results = battery.simulate(
    load_kw=load_df["total_load_kw"],
    generation_kw=total_generation,
)

# results
results = load_df.join(battery_results)

results["wind_generation_kw"] = wind_power
results["solar_generation_kw"] = solar_power
results["total_generation_kw"] = total_generation

# unmet load 
results["unmet_load_kw"] = results["unmet_load_kw"]

# remove startup noise
results = results[pd.to_datetime(STARTUP_CUT):]

# dunkelflaute
start = pd.to_datetime(DUNKEL_START)
end = start + pd.Timedelta(hours=48)

dunkel_load = load_df.loc[start:end, "total_load_kw"]
dunkel_generation = pd.Series(0, index=dunkel_load.index)

dunkel_results = battery.simulate(
    load_kw=dunkel_load,
    generation_kw=dunkel_generation,
)

# system plots
plot_system_balance(results)
plot_unmet_load(results)
plot_load_distribution(load_df)

plot_battery_power(results)         # weekly zoom
plot_battery_power_full(results)    

plot_curtailment(results)
plot_net_balance(results)

plot_dunkelflaute(dunkel_load, dunkel_results)
plot_district_heating(load_df)

# export
results.to_csv("Outputs/hourly_results.csv")
dunkel_results.to_csv("Outputs/dunkelflaute_results.csv")
export_kpis(results, dunkel_results)