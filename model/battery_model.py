import pandas as pd


class BatteryModel:

    def __init__(
        self,
        capacity_kwh=60000,
        power_kw=5000,
        efficiency=0.92,
        initial_soc_fraction=0.60,
    ):
        self.capacity_kwh = capacity_kwh
        self.power_kw = power_kw
        self.efficiency = efficiency
        self.initial_soc = capacity_kwh * initial_soc_fraction

    def simulate(self, load_kw, generation_kw):
        soc = self.initial_soc

        soc_hist = []
        charge_hist = []
        discharge_hist = []
        unmet_hist = []
        curtail_hist = []

        for load, generation in zip(load_kw, generation_kw):
            net = generation - load

            charge = 0
            discharge = 0
            unmet = 0
            curtail = 0

            if net > 0:
                available_capacity = self.capacity_kwh - soc

                charge = min(net, self.power_kw)
                stored = min(charge * self.efficiency, available_capacity)

                soc += stored

                actual_charge_input = stored / self.efficiency if self.efficiency > 0 else 0
                curtail = max(net - actual_charge_input, 0)
                charge = actual_charge_input

            else:
                deficit = -net

                max_deliverable_from_soc = soc * self.efficiency

                discharge = min(
                    deficit,
                    self.power_kw,
                    max_deliverable_from_soc
                )

                soc -= discharge / self.efficiency if self.efficiency > 0 else 0

                unmet = max(deficit - discharge, 0)

            soc = max(0, min(self.capacity_kwh, soc))

            soc_hist.append(soc)
            charge_hist.append(charge)
            discharge_hist.append(discharge)
            unmet_hist.append(unmet)
            curtail_hist.append(curtail)

        return pd.DataFrame({
            "battery_soc_kwh": soc_hist,
            "battery_charge_kw": charge_hist,
            "battery_discharge_kw": discharge_hist,
            "unmet_load_kw": unmet_hist,
            "curtailed_energy_kw": curtail_hist,
        }, index=load_kw.index)