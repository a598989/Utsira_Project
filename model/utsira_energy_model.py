import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ============================================================
# CONFIGURATION
# ============================================================

YEAR = 2023
RANDOM_SEED = 42

# Paths
OUTPUT_FOLDER = Path("../Outputs")
DATA_PATH = Path("../data/The G-Nexus Data Center_Updated (1).csv")

# If running directly inside ChatGPT/Jupyter, this fallback helps.
FALLBACK_DATA_PATH = Path("/mnt/data/The G-Nexus Data Center_Updated (1).csv")

# System sizing
WIND_CAPACITY_KW = 5000
SOLAR_CAPACITY_KW = 1000

BATTERY_CAPACITY_KWH = 60000
BATTERY_POWER_KW = 5000
BATTERY_ROUNDTRIP_EFFICIENCY = 0.92
BATTERY_CHARGE_EFFICIENCY = np.sqrt(BATTERY_ROUNDTRIP_EFFICIENCY)
BATTERY_DISCHARGE_EFFICIENCY = np.sqrt(BATTERY_ROUNDTRIP_EFFICIENCY)
INITIAL_SOC_FRACTION = 0.60

# Data center
TARGET_DATA_CENTER_AVERAGE_KW = 1000

# Residential assumptions
HOUSEHOLDS = 90
HOUSEHOLD_ANNUAL_ELECTRICITY_KWH = 15000
RESIDENTIAL_ANNUAL_TARGET_KWH = HOUSEHOLDS * HOUSEHOLD_ANNUAL_ELECTRICITY_KWH

# EV assumptions
EV_PORTS = 200
EV_CHARGER_POWER_KW = 7.4
EV_ASSUMED_VEHICLES = 200
EV_DAILY_DISTANCE_KM = 6.0
EV_CONSUMPTION_KWH_PER_KM = 0.18
EV_ANNUAL_TARGET_KWH = EV_ASSUMED_VEHICLES * EV_DAILY_DISTANCE_KM * EV_CONSUMPTION_KWH_PER_KM * 365
EV_MAX_SIMULTANEOUS_FRACTION = 0.35

# Industry and infrastructure
INDUSTRY_BASE_LOAD_KW = 150
WATER_SANITATION_LOAD_KW = 40

# Weather/generation calibration
TARGET_WIND_CAPACITY_FACTOR = 0.36
TARGET_SOLAR_CAPACITY_FACTOR = 0.105

# Plot style
plt.rcParams.update(
    {
        "figure.dpi": 120,
        "savefig.dpi": 220,
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def ensure_output_folder() -> None:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def get_data_path() -> Path:
    if DATA_PATH.exists():
        return DATA_PATH
    if FALLBACK_DATA_PATH.exists():
        return FALLBACK_DATA_PATH
    return DATA_PATH


def save_plot(filename: str) -> None:
    plt.tight_layout()
    plt.savefig(OUTPUT_FOLDER / filename, bbox_inches="tight")
    plt.close()


def format_date_axis(ax, mode: str = "month") -> None:
    if mode == "day":
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
    elif mode == "month":
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    elif mode == "month_short":
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.tick_params(axis="x", rotation=45)


def scale_to_annual_energy(series: pd.Series, target_kwh: float) -> pd.Series:
    current = float(series.sum())
    if current <= 0:
        return series
    return series * (target_kwh / current)


def scale_to_average_power(series: pd.Series, target_average_kw: float) -> pd.Series:
    current = float(series.mean())
    if current <= 0:
        return series
    return series * (target_average_kw / current)


def smooth(series: pd.Series, window: int = 24) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


# ============================================================
# INPUT DATA
# ============================================================

def load_data_center() -> pd.DataFrame:
    """
    Loads the provided G-Nexus data center file.

    The CSV values are scaled so that the data center electrical load has an
    annual average of 1 MW, as required by the project description.
    """
    path = get_data_path()

    if not path.exists():
        print("WARNING: Data center CSV not found. Creating synthetic 1 MW data center load.")
        index = pd.date_range(
            f"{YEAR}-01-01 00:00",
            f"{YEAR}-12-31 23:00",
            freq="1h",
        )
        return pd.DataFrame(
            {
                "it_electrical_load_kw": np.full(len(index), TARGET_DATA_CENTER_AVERAGE_KW),
                "cooling_thermal_load_kw": np.full(len(index), TARGET_DATA_CENTER_AVERAGE_KW * 0.95),
                "waste_heat_available_kw": np.full(len(index), TARGET_DATA_CENTER_AVERAGE_KW * 0.65),
            },
            index=index,
        )

    df = pd.read_csv(path)

    if "timestamp" not in df.columns:
        raise ValueError("CSV must contain a 'timestamp' column.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.set_index("timestamp")

    df.index = df.index.tz_convert("Europe/Oslo").tz_localize(None)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df = df[numeric_cols].resample("1h").mean()

    required = ["it_electrical_load_kw"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"CSV must contain '{col}'.")

    df = df.dropna(subset=["it_electrical_load_kw"])

    scale_factor = TARGET_DATA_CENTER_AVERAGE_KW / df["it_electrical_load_kw"].mean()

    for col in ["it_electrical_load_kw", "cooling_thermal_load_kw", "waste_heat_available_kw"]:
        if col in df.columns:
            df[col] = df[col] * scale_factor

    if "cooling_thermal_load_kw" not in df.columns:
        df["cooling_thermal_load_kw"] = df["it_electrical_load_kw"] * 0.95

    if "waste_heat_available_kw" not in df.columns:
        df["waste_heat_available_kw"] = df["it_electrical_load_kw"] * 0.65

    return df


def create_simulation_index_from_data_center(dc: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Uses the data center time index directly. This keeps all plots consistent
    with the provided dataset.
    """
    return dc.index


# ============================================================
# WEATHER MODEL
# ============================================================

def get_synthetic_utsira_weather(index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Synthetic Utsira-like weather.

    This is not measured weather data. It is a reproducible fallback model
    calibrated to Norwegian coastal seasonal patterns:
      - colder in Jan-Feb
      - stronger wind in winter
      - solar production concentrated in summer
    """
    rng = np.random.default_rng(RANDOM_SEED)

    n = len(index)
    hour = index.hour.to_numpy()
    day = index.dayofyear.to_numpy()

    # Temperature: coldest around mid-January/February, warmest in July/August.
    temperature = 7.0 + 6.5 * np.sin(2 * np.pi * (day - 105) / 365)
    temperature += rng.normal(0, 1.2, n)

    # Wind: coastal, stronger in winter, stochastic but bounded.
    seasonal_wind = 7.8 + 1.7 * np.cos(2 * np.pi * (day - 20) / 365)
    synoptic_variability = rng.normal(0, 1.8, n)

    # Add slow weather systems to avoid purely white-noise wind.
    slow = pd.Series(rng.normal(0, 1.0, n)).rolling(18, min_periods=1).mean().to_numpy()
    wind_speed_10m = np.clip(seasonal_wind + synoptic_variability + slow, 0, 25)

    # Solar: seasonal and diurnal. Very weak in winter.
    seasonal_solar = np.maximum(0, np.sin(2 * np.pi * (day - 78) / 365))
    daily_solar = np.maximum(0, np.sin(np.pi * (hour - 6) / 12))

    cloud_factor = rng.uniform(0.45, 1.0, n)
    cloud_slow = pd.Series(rng.uniform(0.75, 1.05, n)).rolling(6, min_periods=1).mean().to_numpy()

    shortwave_radiation = 760 * seasonal_solar * daily_solar * cloud_factor * cloud_slow
    shortwave_radiation = np.clip(shortwave_radiation, 0, 1000)

    return pd.DataFrame(
        {
            "temperature_2m": temperature,
            "wind_speed_10m": wind_speed_10m,
            "shortwave_radiation": shortwave_radiation,
        },
        index=index,
    )


# ============================================================
# LOAD MODELS
# ============================================================

def residential_load(index: pd.DatetimeIndex, temperature: pd.Series) -> pd.Series:
    """
    Residential load for 90 households, scaled to 15 MWh/household/year.

    Shape includes:
      - temperature-dependent heating demand
      - morning peak
      - evening peak
      - small stochastic variation
    """
    rng = np.random.default_rng(RANDOM_SEED + 10)

    hour = index.hour.to_numpy()
    temp = temperature.to_numpy()

    base = np.full(len(index), 1.0)

    heating_degree = np.maximum(0, 15 - temp)
    heating_shape = 0.08 * heating_degree

    morning_peak = 0.22 * np.exp(-0.5 * ((hour - 7) / 2.0) ** 2)
    evening_peak = 0.32 * np.exp(-0.5 * ((hour - 19) / 2.6) ** 2)

    random_factor = rng.normal(1.0, 0.04, len(index))
    raw = (base + heating_shape + morning_peak + evening_peak) * random_factor
    raw = np.clip(raw, 0, None)

    load = pd.Series(raw, index=index, name="residential")
    load = scale_to_annual_energy(load, RESIDENTIAL_ANNUAL_TARGET_KWH)
    return load


def ev_load(index: pd.DatetimeIndex) -> pd.Series:
    """
    EV load model.

    The island has 200 charging points, but the energy demand is based on
    short local driving distances. The model creates evening-biased charging
    and scales the annual energy to a realistic island-driving assumption.
    """
    rng = np.random.default_rng(RANDOM_SEED + 20)

    load = np.zeros(len(index))
    max_plausible_power = EV_PORTS * EV_CHARGER_POWER_KW * EV_MAX_SIMULTANEOUS_FRACTION

    unique_days = pd.Index(index.date).unique()

    for date in unique_days:
        mask = np.array(index.date) == date
        hours = index[mask].hour.to_numpy()

        # Not every vehicle needs charging every day.
        daily_activity = rng.uniform(0.25, 1.0)

        evening = np.exp(-0.5 * ((hours - 19) / 2.0) ** 2)
        night_tail = 0.25 * np.exp(-0.5 * ((hours - 23) / 3.0) ** 2)

        shape = evening + night_tail
        shape = shape / max(shape.max(), 1e-9)

        load[mask] = max_plausible_power * daily_activity * shape

    series = pd.Series(load, index=index, name="ev")
    series = scale_to_annual_energy(series, EV_ANNUAL_TARGET_KWH)

    # Ensure power does not exceed assumed simultaneity.
    series = series.clip(upper=max_plausible_power)
    return series


def industrial_load(index: pd.DatetimeIndex) -> pd.Series:
    """
    Constant industrial base load for fish processing / local industry.
    """
    return pd.Series(INDUSTRY_BASE_LOAD_KW, index=index, name="industry")


def water_sanitation_load(index: pd.DatetimeIndex) -> pd.Series:
    """
    Constant water and wastewater infrastructure load.
    """
    return pd.Series(WATER_SANITATION_LOAD_KW, index=index, name="water_sanitation")


# ============================================================
# GENERATION MODELS
# ============================================================

def hub_height_wind_speed(v10: pd.Series, z_ref: float = 10.0, z_hub: float = 90.0, alpha: float = 0.14) -> pd.Series:
    """
    Power-law wind shear correction from 10 m to hub height.
    """
    return v10 * (z_hub / z_ref) ** alpha


def raw_wind_power_from_speed(v_hub: pd.Series) -> pd.Series:
    """
    Simple turbine power curve for the 5 MW wind farm.
    """
    v = v_hub.to_numpy(dtype=float)

    cut_in = 3.0
    rated = 12.0
    cut_out = 25.0

    p = np.zeros(len(v))

    ramp = (v >= cut_in) & (v < rated)
    p[ramp] = WIND_CAPACITY_KW * ((v[ramp] - cut_in) / (rated - cut_in)) ** 3

    rated_region = (v >= rated) & (v < cut_out)
    p[rated_region] = WIND_CAPACITY_KW

    return pd.Series(p, index=v_hub.index, name="wind_raw")


def wind_power(v10: pd.Series) -> pd.Series:
    """
    Wind power calibrated to a target annual capacity factor, while respecting
    installed capacity.
    """
    v_hub = hub_height_wind_speed(v10)
    raw = raw_wind_power_from_speed(v_hub)

    target_annual_kwh = WIND_CAPACITY_KW * len(raw) * TARGET_WIND_CAPACITY_FACTOR
    scaled = scale_to_annual_energy(raw, target_annual_kwh)
    scaled = scaled.clip(lower=0, upper=WIND_CAPACITY_KW)
    scaled.name = "wind"
    return scaled


def raw_solar_power_from_radiation(radiation: pd.Series) -> pd.Series:
    p = SOLAR_CAPACITY_KW * (radiation / 1000.0)
    return pd.Series(np.clip(p, 0, SOLAR_CAPACITY_KW), index=radiation.index, name="solar_raw")


def solar_power(radiation: pd.Series) -> pd.Series:
    """
    PV output calibrated to a realistic annual PV capacity factor for Norway.
    """
    raw = raw_solar_power_from_radiation(radiation)

    target_annual_kwh = SOLAR_CAPACITY_KW * len(raw) * TARGET_SOLAR_CAPACITY_FACTOR
    scaled = scale_to_annual_energy(raw, target_annual_kwh)
    scaled = scaled.clip(lower=0, upper=SOLAR_CAPACITY_KW)
    scaled.name = "solar"
    return scaled


# ============================================================
# BATTERY DISPATCH
# ============================================================

def battery_dispatch(load_kw: pd.Series, generation_kw: pd.Series, initial_soc_kwh: float | None = None) -> pd.DataFrame:
    """
    Sequential hourly BESS dispatch.

    Positive surplus charges the battery.
    Deficit discharges the battery.
    Charge/discharge are never simultaneous in the same hour.
    """
    if initial_soc_kwh is None:
        soc = BATTERY_CAPACITY_KWH * INITIAL_SOC_FRACTION
    else:
        soc = float(initial_soc_kwh)

    soc_values = []
    charge_values = []
    discharge_values = []
    unmet_values = []
    curtailment_values = []

    for load, gen in zip(load_kw.to_numpy(), generation_kw.to_numpy()):
        surplus = gen - load

        charge = 0.0
        discharge = 0.0
        unmet = 0.0
        curtailment = 0.0

        if surplus > 0:
            max_charge_by_capacity = (BATTERY_CAPACITY_KWH - soc) / BATTERY_CHARGE_EFFICIENCY
            charge = min(surplus, BATTERY_POWER_KW, max_charge_by_capacity)
            soc += charge * BATTERY_CHARGE_EFFICIENCY
            curtailment = max(0.0, surplus - charge)

        elif surplus < 0:
            deficit = -surplus
            max_discharge_by_soc = soc * BATTERY_DISCHARGE_EFFICIENCY
            discharge = min(deficit, BATTERY_POWER_KW, max_discharge_by_soc)
            soc -= discharge / BATTERY_DISCHARGE_EFFICIENCY
            unmet = max(0.0, deficit - discharge)

        soc = min(max(soc, 0.0), BATTERY_CAPACITY_KWH)

        soc_values.append(soc)
        charge_values.append(charge)
        discharge_values.append(discharge)
        unmet_values.append(unmet)
        curtailment_values.append(curtailment)

    return pd.DataFrame(
        {
            "soc": soc_values,
            "battery_charge": charge_values,
            "battery_discharge": discharge_values,
            "unmet": unmet_values,
            "curtailment": curtailment_values,
        },
        index=load_kw.index,
    )


def run_dunkelflaute_test(df: pd.DataFrame) -> pd.DataFrame:
    """
    48-hour winter stress test with renewable generation forced to zero.
    Starts with a full battery to test the assignment requirement:
    can critical/full load survive 48 hours without generation?
    """
    start = pd.Timestamp(f"{YEAR}-01-15 00:00")
    end = start + pd.Timedelta(hours=47)

    if start < df.index.min() or end > df.index.max():
        start = df.index[0]
        end = start + pd.Timedelta(hours=47)

    dunkel = df.loc[start:end].copy()
    forced_generation = pd.Series(0.0, index=dunkel.index, name="forced_generation")

    dispatch = battery_dispatch(
        load_kw=dunkel["total_load"],
        generation_kw=forced_generation,
        initial_soc_kwh=BATTERY_CAPACITY_KWH,
    )

    dunkel["forced_generation"] = forced_generation
    dunkel["dunkel_soc"] = dispatch["soc"]
    dunkel["dunkel_unmet"] = dispatch["unmet"]
    dunkel["dunkel_discharge"] = dispatch["battery_discharge"]

    return dunkel


# ============================================================
# PLOTS
# ============================================================

def make_plots(df: pd.DataFrame, dunkel: pd.DataFrame) -> None:
    # --------------------------------------------------------
    # 01 Annual load
    # --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df["total_load"], linewidth=0.7, label="Total load [kW]")
    ax.set_title("Annual Load")
    ax.set_xlabel("Time")
    ax.set_ylabel("Power [kW]")
    ax.set_ylim(0, df["total_load"].max() * 1.15)
    ax.legend(loc="upper right")
    format_date_axis(ax, "month")
    save_plot("01_annual_load.png")

    # --------------------------------------------------------
    # 02 Renewable generation
    # --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, smooth(df["wind"], 24), label="Wind [kW]", linewidth=1.0)
    ax.plot(df.index, smooth(df["solar"], 24), label="Solar [kW]", linewidth=1.0)
    ax.plot(df.index, smooth(df["generation"], 24), label="Total generation [kW]", linewidth=1.3)
    ax.set_title("Renewable Generation")
    ax.set_xlabel("Time")
    ax.set_ylabel("Power [kW]")
    ax.legend(loc="upper right")
    format_date_axis(ax, "month")
    save_plot("02_renewable_generation.png")

    # --------------------------------------------------------
    # 03 Battery SOC
    # --------------------------------------------------------
    soc_mwh = df["soc"] / 1000.0

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, soc_mwh, linewidth=0.8, label="Battery SOC [MWh]")
    ax.axhline(soc_mwh.min(), linewidth=1.2, label=f"Minimum SOC = {soc_mwh.min():.1f} MWh")
    ax.axhline(BATTERY_CAPACITY_KWH / 1000, linewidth=1.2, label="Maximum SOC = 60.0 MWh")
    ax.set_title("Battery State of Charge")
    ax.set_xlabel("Time")
    ax.set_ylabel("Energy [MWh]")
    ax.set_ylim(0, BATTERY_CAPACITY_KWH / 1000 * 1.05)
    ax.legend(loc="upper right")
    format_date_axis(ax, "month")
    save_plot("03_battery_soc.png")

    # --------------------------------------------------------
    # 04 Load, generation and SOC overlay
    # --------------------------------------------------------
    window = df.loc[f"{YEAR}-01-01":f"{YEAR}-01-14 23:00"].copy()
    if window.empty:
        window = df.iloc[: min(len(df), 24 * 14)].copy()

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(window.index, window["total_load"], label="Load [kW]", linewidth=1.6)
    ax1.plot(window.index, window["generation"], label="Generation [kW]", linewidth=1.3)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [kW]")

    ax2 = ax1.twinx()
    ax2.plot(window.index, window["soc"] / 1000.0, label="Battery SOC [MWh]", linewidth=1.8)
    ax2.set_ylabel("Battery SOC [MWh]")
    ax2.set_ylim(0, BATTERY_CAPACITY_KWH / 1000 * 1.05)

    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, loc="upper left")

    ax1.set_title("Load, Generation and Battery SOC (Two-Week Window)")
    format_date_axis(ax1, "day")
    save_plot("04_load_generation_soc_overlay.png")

    # --------------------------------------------------------
    # 05 Corrected load pie chart
    # --------------------------------------------------------
    sector_energy = {
        "Data center": df["it_electrical_load_kw"].sum(),
        "Residential": df["residential"].sum(),
        "EV charging": df["ev"].sum(),
        "Industry": df["industry"].sum(),
        "Water & sanitation": df["water_sanitation"].sum(),
    }

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(
        list(sector_energy.values()),
        labels=list(sector_energy.keys()),
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.set_title("Annual Load Distribution by Sector")
    save_plot("05_load_pie.png")

    # --------------------------------------------------------
    # 06 Average daily profile
    # --------------------------------------------------------
    daily = df.groupby(df.index.hour)[["total_load", "generation", "ev", "residential"]].mean()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(daily.index, daily["total_load"], marker="o", label="Total load [kW]")
    ax.plot(daily.index, daily["generation"], marker="o", label="Generation [kW]")
    ax.plot(daily.index, daily["residential"], marker="o", label="Residential [kW]")
    ax.plot(daily.index, daily["ev"], marker="o", label="EV charging [kW]")
    ax.set_title("Average Daily Profile")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Power [kW]")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(loc="upper left")
    save_plot("06_daily_profile.png")

    # --------------------------------------------------------
    # 07 Monthly load and generation
    # --------------------------------------------------------
    monthly = df.resample("ME")[["total_load", "generation"]].sum() / 1000.0

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(monthly))
    labels = [d.strftime("%m/%y") for d in monthly.index]

    ax.bar(x - 0.2, monthly["total_load"], width=0.4, label="Load [MWh]")
    ax.bar(x + 0.2, monthly["generation"], width=0.4, label="Generation [MWh]")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45)
    ax.set_title("Monthly Load and Generation")
    ax.set_xlabel("Month")
    ax.set_ylabel("Energy [MWh]")
    ax.legend(loc="upper right")
    save_plot("07_monthly_load_generation.png")

    # --------------------------------------------------------
    # 08 Dunkelflaute stress test
    # --------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(dunkel.index, dunkel["total_load"], label="Load [kW]", linewidth=2)
    ax1.plot(dunkel.index, dunkel["forced_generation"], label="Forced generation [kW]", linewidth=2)
    ax1.plot(dunkel.index, dunkel["dunkel_unmet"], label="Unmet load [kW]", linewidth=2)
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [kW]")

    ax2 = ax1.twinx()
    ax2.plot(dunkel.index, dunkel["dunkel_soc"] / 1000.0, label="Battery SOC [MWh]", linewidth=2)
    ax2.set_ylabel("Battery SOC [MWh]")
    ax2.set_ylim(0, BATTERY_CAPACITY_KWH / 1000 * 1.05)

    l1, lab1 = ax1.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lab1 + lab2, loc="upper right")

    ax1.set_title("48-hour Dunkelflaute Stress Test: Battery-Only Operation")
    format_date_axis(ax1, "day")
    save_plot("08_dunkelflaute_stress_test.png")

    # --------------------------------------------------------
    # 09 Unmet load
    # --------------------------------------------------------
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df["unmet"], linewidth=0.7, label="Unmet load [kW]")

    if df["unmet"].max() <= 1e-9:
        ax.text(
            0.5,
            0.5,
            "No unmet load in normal operation",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=12,
        )
        ax.set_ylim(0, 1)
    else:
        ax.set_ylim(0, df["unmet"].max() * 1.15)

    ax.set_title("Unmet Load Over the Simulation Period")
    ax.set_xlabel("Time")
    ax.set_ylabel("Unmet load [kW]")
    ax.legend(loc="upper right")
    format_date_axis(ax, "month")
    save_plot("09_unmet_load.png")

    # --------------------------------------------------------
    # 10 Battery charge/discharge
    # Daily mean is used to make the annual plot readable.
    # This is honest: charge and discharge can both occur on the same day,
    # but not simultaneously in the model.
    # --------------------------------------------------------
    daily_battery = df[["battery_charge", "battery_discharge"]].resample("D").mean()

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(daily_battery.index, daily_battery["battery_charge"], label="Battery charge [kW]")
    ax.plot(daily_battery.index, daily_battery["battery_discharge"], label="Battery discharge [kW]")
    ax.set_title("Battery Charge and Discharge Power (Daily Average)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Power [kW]")
    ax.legend(loc="upper right")
    format_date_axis(ax, "month")
    save_plot("10_battery_charge_discharge.png")

    # --------------------------------------------------------
    # 11 Winter week dispatch
    # --------------------------------------------------------
    winter_week = df.loc[f"{YEAR}-01-15":f"{YEAR}-01-21 23:00"].copy()
    if not winter_week.empty:
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.plot(winter_week.index, winter_week["total_load"], label="Load [kW]", linewidth=1.6)
        ax1.plot(winter_week.index, winter_week["generation"], label="Generation [kW]", linewidth=1.3)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Power [kW]")

        ax2 = ax1.twinx()
        ax2.plot(winter_week.index, winter_week["soc"] / 1000.0, label="Battery SOC [MWh]", linewidth=1.8)
        ax2.set_ylabel("Battery SOC [MWh]")
        ax2.set_ylim(0, BATTERY_CAPACITY_KWH / 1000 * 1.05)

        l1, lab1 = ax1.get_legend_handles_labels()
        l2, lab2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lab1 + lab2, loc="upper left")

        ax1.set_title("Typical Winter Week Dispatch")
        format_date_axis(ax1, "day")
        save_plot("11_winter_week_dispatch.png")

    # --------------------------------------------------------
    # 12 Summer week dispatch
    # --------------------------------------------------------
    summer_week = df.loc[f"{YEAR}-07-15":f"{YEAR}-07-21 23:00"].copy()
    if not summer_week.empty:
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.plot(summer_week.index, summer_week["total_load"], label="Load [kW]", linewidth=1.6)
        ax1.plot(summer_week.index, summer_week["generation"], label="Generation [kW]", linewidth=1.3)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Power [kW]")

        ax2 = ax1.twinx()
        ax2.plot(summer_week.index, summer_week["soc"] / 1000.0, label="Battery SOC [MWh]", linewidth=1.8)
        ax2.set_ylabel("Battery SOC [MWh]")
        ax2.set_ylim(0, BATTERY_CAPACITY_KWH / 1000 * 1.05)

        l1, lab1 = ax1.get_legend_handles_labels()
        l2, lab2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lab1 + lab2, loc="upper left")

        ax1.set_title("Typical Summer Week Dispatch")
        format_date_axis(ax1, "day")
        save_plot("12_summer_week_dispatch.png")


# ============================================================
# TABLE EXPORTS
# ============================================================

def export_summary_tables(df: pd.DataFrame, dunkel: pd.DataFrame) -> None:
    annual_load_mwh = df["total_load"].sum() / 1000.0
    annual_generation_mwh = df["generation"].sum() / 1000.0
    annual_unmet_mwh = df["unmet"].sum() / 1000.0
    reliability = 100.0 * (1.0 - annual_unmet_mwh / annual_load_mwh)

    summary = pd.DataFrame(
        {
            "Metric": [
                "Annual load",
                "Annual renewable generation",
                "Annual unmet load",
                "Reliability",
                "Average load",
                "Peak load",
                "Minimum SOC",
                "Dunkelflaute minimum SOC",
                "Dunkelflaute unmet load",
            ],
            "Value": [
                f"{annual_load_mwh:.1f} MWh",
                f"{annual_generation_mwh:.1f} MWh",
                f"{annual_unmet_mwh:.2f} MWh",
                f"{reliability:.3f} %",
                f"{df['total_load'].mean():.1f} kW",
                f"{df['total_load'].max():.1f} kW",
                f"{df['soc'].min() / 1000.0:.1f} MWh",
                f"{dunkel['dunkel_soc'].min() / 1000.0:.1f} MWh",
                f"{dunkel['dunkel_unmet'].sum() / 1000.0:.2f} MWh",
            ],
        }
    )

    sector = pd.DataFrame(
        {
            "Sector": [
                "Data center",
                "Residential",
                "EV charging",
                "Industry",
                "Water & sanitation",
            ],
            "Annual energy [MWh]": [
                df["it_electrical_load_kw"].sum() / 1000.0,
                df["residential"].sum() / 1000.0,
                df["ev"].sum() / 1000.0,
                df["industry"].sum() / 1000.0,
                df["water_sanitation"].sum() / 1000.0,
            ],
        }
    )
    sector["Share [%]"] = 100 * sector["Annual energy [MWh]"] / sector["Annual energy [MWh]"].sum()

    summary.to_csv(OUTPUT_FOLDER / "summary_metrics.csv", index=False)
    sector.to_csv(OUTPUT_FOLDER / "sector_energy.csv", index=False)

    with open(OUTPUT_FOLDER / "summary_metrics.tex", "w", encoding="utf-8") as f:
        f.write(summary.to_latex(index=False, escape=False))

    with open(OUTPUT_FOLDER / "sector_energy.tex", "w", encoding="utf-8") as f:
        f.write(sector.to_latex(index=False, float_format="%.2f"))


# ============================================================
# MAIN SIMULATION
# ============================================================

def run() -> pd.DataFrame:
    ensure_output_folder()

    dc = load_data_center()
    index = create_simulation_index_from_data_center(dc)

    weather = get_synthetic_utsira_weather(index)

    df = dc.copy()
    df = df.join(weather)

    df["wind"] = wind_power(df["wind_speed_10m"])
    df["solar"] = solar_power(df["shortwave_radiation"])
    df["generation"] = df["wind"] + df["solar"]

    df["residential"] = residential_load(df.index, df["temperature_2m"])
    df["ev"] = ev_load(df.index)
    df["industry"] = industrial_load(df.index)
    df["water_sanitation"] = water_sanitation_load(df.index)

    df["total_load"] = (
        df["it_electrical_load_kw"]
        + df["residential"]
        + df["ev"]
        + df["industry"]
        + df["water_sanitation"]
    )

    dispatch = battery_dispatch(df["total_load"], df["generation"])

    for col in dispatch.columns:
        df[col] = dispatch[col]

    dunkel = run_dunkelflaute_test(df)

    df.to_csv(OUTPUT_FOLDER / "results.csv")
    dunkel.to_csv(OUTPUT_FOLDER / "dunkelflaute_results.csv")

    make_plots(df, dunkel)
    export_summary_tables(df, dunkel)

    annual_load_mwh = df["total_load"].sum() / 1000.0
    annual_generation_mwh = df["generation"].sum() / 1000.0
    annual_unmet_mwh = df["unmet"].sum() / 1000.0
    reliability = 100.0 * (1.0 - annual_unmet_mwh / annual_load_mwh)

    print("\nSUCCESS")
    print(f"Outputs saved in: {OUTPUT_FOLDER.resolve()}")
    print(f"Rows simulated: {len(df)}")
    print(f"Average load: {df['total_load'].mean():.2f} kW")
    print(f"Peak load: {df['total_load'].max():.2f} kW")
    print(f"Annual load: {annual_load_mwh:.2f} MWh")
    print(f"Annual generation: {annual_generation_mwh:.2f} MWh")
    print(f"Unmet load: {annual_unmet_mwh:.2f} MWh")
    print(f"Reliability: {reliability:.3f} %")
    print(f"Minimum battery SOC: {df['soc'].min() / 1000.0:.2f} MWh")
    print(f"Dunkelflaute minimum SOC: {dunkel['dunkel_soc'].min() / 1000.0:.2f} MWh")
    print(f"Dunkelflaute unmet load: {dunkel['dunkel_unmet'].sum() / 1000.0:.2f} MWh")

    print("\nSector energy:")
    sector = pd.read_csv(OUTPUT_FOLDER / "sector_energy.csv")
    print(sector.to_string(index=False))

    return df


if __name__ == "__main__":
    run()