import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates

# config
FIGSIZE = (12, 5)
DATE_FULL = mdates.DateFormatter("%d/%m/%Y")
DATE_MONTH = mdates.DateFormatter("%m/%Y")


# helpers
def _finalize_plot(filename):
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"Outputs/{filename}", dpi=300)
    plt.show()


# wind
def plot_wind_power(wind):
    plt.figure(figsize=FIGSIZE)
    plt.plot(wind, label="Wind [kW]")

    plt.title("Wind Power")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    _finalize_plot("wind_power.png")


# solar
def plot_solar_power(solar):
    plt.figure(figsize=FIGSIZE)
    plt.plot(solar, color="orange", label="Solar [kW]")

    plt.title("Solar PV Generation")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    _finalize_plot("solar_power.png")


# total generation
def plot_total_generation(wind, solar):
    total = wind + solar

    plt.figure(figsize=FIGSIZE)
    plt.plot(wind, label="Wind")
    plt.plot(solar, label="Solar")
    plt.plot(total, linewidth=2, label="Total")

    plt.title("Total Generation")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    _finalize_plot("total_generation.png")


# stacked generation
def plot_generation_stack(wind, solar):
    plt.figure(figsize=(12, 6))

    plt.stackplot(
        wind.index,
        wind,
        solar,
        labels=["Wind", "Solar"],
        colors=["tab:blue", "orange"],
        alpha=0.85,
    )

    plt.title("Generation Composition")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend(loc="upper left")
    plt.grid()

    _finalize_plot("stacked_generation.png")


# weekly profile
def plot_week(wind, solar, start_date):
    start = pd.to_datetime(start_date, dayfirst=True)
    end = start + pd.Timedelta(days=7)

    w = wind[start:end]
    s = solar[start:end]

    plt.figure(figsize=FIGSIZE)
    plt.plot(w, label="Wind")
    plt.plot(s, label="Solar")

    plt.title(f"Week: {start.strftime('%d/%m/%Y')}")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    ax = plt.gca()
    ax.xaxis.set_major_formatter(DATE_FULL)
    ax.xaxis.set_major_locator(mdates.DayLocator())

    _finalize_plot(f"week_{start_date}.png")


# monthly energy
def plot_monthly(wind, solar):
    w = wind.resample("ME").sum() / 1000
    s = solar.resample("ME").sum() / 1000
    total = w + s

    plt.figure(figsize=FIGSIZE)
    plt.plot(w, marker="o", label="Wind")
    plt.plot(s, marker="o", label="Solar")
    plt.plot(total, marker="o", linewidth=2, label="Total")

    plt.title("Monthly Energy")
    plt.xlabel("Time")
    plt.ylabel("Energy [MWh]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_MONTH)

    _finalize_plot("monthly_generation.png")


# system balance
def plot_system_balance(results):
    load = results["total_load_kw"].resample("1D").mean()
    gen = results["total_generation_kw"].resample("1D").mean()
    soc = results["battery_soc_kwh"].resample("1D").mean() / 1000

    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.plot(load, label="Load [kW]", linewidth=2)
    ax1.plot(gen, label="Generation [kW]", linewidth=2)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [kW]")
    ax1.grid()

    ax2 = ax1.twinx()
    ax2.plot(soc, label="Battery SOC [MWh]", color="green", linewidth=2)

    ax2.set_ylabel("Battery SOC [MWh]")
    ax2.set_ylim(0, soc.max() * 1.1)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.20),
        ncol=3,
    )

    plt.title("System Balance (Daily Average)", pad=35)

    ax1.xaxis.set_major_formatter(DATE_MONTH)

    plt.tight_layout()
    plt.savefig("Outputs/system_balance.png", dpi=300)
    plt.show()


# unmet load
def plot_unmet_load(results):
    unmet = results["unmet_load_kw"].resample("D").sum() / 1000

    plt.figure(figsize=FIGSIZE)
    plt.plot(unmet, color="red", label="Unmet [MWh/day]")

    plt.title("Unmet Energy")
    plt.xlabel("Time")
    plt.ylabel("MWh/day")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_MONTH)

    _finalize_plot("unmet_load.png")


# load distribution
def plot_load_distribution(load_df):
    values = [
        load_df["data_center_kw"].sum(),
        load_df["residential_kw"].sum(),
        load_df["industry_kw"].sum(),
        load_df["water_kw"].sum(),
        load_df["ev_kw"].sum(),
    ]

    labels = ["Data center", "Residential", "Industry", "Water", "EV"]

    plt.figure(figsize=(7, 7))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)

    plt.title("Load Distribution")

    _finalize_plot("load_distribution.png")


# battery power (weekly zoom)
def plot_battery_power(results):
    sample = results["2023-01-10":"2023-01-17"]

    plt.figure(figsize=FIGSIZE)
    plt.plot(sample["battery_charge_kw"], label="Charge [kW]", linewidth=2)
    plt.plot(sample["battery_discharge_kw"], label="Discharge [kW]", linewidth=2)

    plt.title("Battery Operation (Winter Week)")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))

    _finalize_plot("battery_power_week.png")


# battery power (full year)
def plot_battery_power_full(results):
    plt.figure(figsize=FIGSIZE)

    plt.plot(results["battery_charge_kw"], label="Charge [kW]", linewidth=1.5)
    plt.plot(results["battery_discharge_kw"], label="Discharge [kW]", linewidth=1.5)

    plt.title("Battery Operation (Full Year)")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_MONTH)

    _finalize_plot("battery_power_full.png")


# curtailment
def plot_curtailment(results):
    curtail = results["curtailed_energy_kw"].resample("1D").sum() / 1000

    plt.figure(figsize=FIGSIZE)
    plt.plot(curtail, label="Curtailed [MWh/day]", linewidth=2)

    plt.title("Curtailed Energy")
    plt.xlabel("Time")
    plt.ylabel("Energy [MWh]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_MONTH)

    _finalize_plot("curtailment.png")


# net balance
def plot_net_balance(results):
    net = results["total_generation_kw"] - results["total_load_kw"]
    net = net.resample("1D").mean()

    plt.figure(figsize=FIGSIZE)
    plt.plot(net, label="Net [kW]", linewidth=2)
    plt.axhline(0, linestyle="--")

    plt.title("Net Power Balance")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_MONTH)

    _finalize_plot("net_balance.png")


# dunkelflaute
def plot_dunkelflaute(load, results):
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(load.index, load, label="Load [kW]", linewidth=2)
    ax1.plot(results.index, results["unmet_load_kw"], label="Unmet load [kW]", color="red", linewidth=2)

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Power [kW]")
    ax1.grid()

    ax2 = ax1.twinx()
    ax2.plot(
        results.index,
        results["battery_soc_kwh"] / 1000,
        label="Battery SOC [MWh]",
        color="green",
        linewidth=2,
    )

    ax2.set_ylabel("Energy [MWh]")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()

    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")

    plt.title("48h Dunkelflaute (Battery Only)")

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=6))

    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig("Outputs/dunkelflaute.png", dpi=300)
    plt.show()

# district heating
def plot_district_heating(load_df):
    start = pd.to_datetime("2023-01-10")
    end = start + pd.Timedelta(days=7)

    load = load_df.loc[start:end, "total_load_kw"]
    reduced = (load - 600).clip(lower=0)

    plt.figure(figsize=FIGSIZE)
    plt.plot(load, label="Original")
    plt.plot(reduced, label="With DH")

    plt.title("District Heating Impact")
    plt.xlabel("Time")
    plt.ylabel("Power [kW]")
    plt.legend()
    plt.grid()

    plt.gca().xaxis.set_major_formatter(DATE_FULL)

    _finalize_plot("district_heating.png")