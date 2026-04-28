import pandas as pd


def export_kpis(results, dunkel_results, output_path="Outputs/kpi_summary.csv"):
    total_gen = results["total_generation_kw"].sum()
    total_load = results["total_load_kw"].sum()
    unmet = results["unmet_load_kw"].sum()
    curtail = results["curtailed_energy_kw"].sum()

    kpi_data = {
        "Metric": [
            "Annual load [MWh]",
            "Annual unmet load [MWh]",
            "System reliability [%]",
            "Min battery SOC [MWh]",
            "Max battery SOC [MWh]",
            "Total generation [MWh]",
            "Total load [MWh]",
            "Unmet load [MWh]",
            "Curtailed energy [MWh]",
            "Self-sufficiency [%]",
            "Curtailment ratio [%]",
            "Loss of load probability [%]",
            "Dunkelflaute initial SOC [MWh]",
            "Dunkelflaute final SOC [MWh]",
            "Dunkelflaute unmet load [MWh]"
        ],
        "Value": [
            total_load / 1000,
            unmet / 1000,
            100 * (1 - unmet / total_load),
            results["battery_soc_kwh"].min() / 1000,
            results["battery_soc_kwh"].max() / 1000,
            total_gen / 1000,
            total_load / 1000,
            unmet / 1000,
            curtail / 1000,
            (1 - unmet / total_load) * 100,
            curtail / total_gen * 100,
            (results["unmet_load_kw"] > 0).mean() * 100,
            dunkel_results["battery_soc_kwh"].iloc[0] / 1000,
            dunkel_results["battery_soc_kwh"].iloc[-1] / 1000,
            dunkel_results["unmet_load_kw"].sum() / 1000
        ]
    }

    kpi_df = pd.DataFrame(kpi_data)
    kpi_df.to_csv(output_path, index=False)

    print(f"KPI file saved to {output_path}")