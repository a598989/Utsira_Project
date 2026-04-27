class BatteryModel:
    

    def __init__(self, capacity_mwh=60, efficiency=0.92):
        self.capacity = capacity_mwh
        self.soc = capacity_mwh * 0.6
        self.eff = efficiency

    def step(self, generation_kw, load_kw):

        net = generation_kw - load_kw

        if net > 0:
            charge = min(net / 1000, self.capacity - self.soc)
            self.soc += charge * self.eff
            return charge * 1000, 0

        else:
            discharge = min(-net / 1000, self.soc)
            self.soc -= discharge
            return 0, discharge * 1000