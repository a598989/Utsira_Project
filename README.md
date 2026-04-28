# G-Nexus Utsira Project – Energy System Simulation

## Overview

This project presents the modelling and simulation of a 100% renewable, off-grid energy system for the island of Utsira, Norway, as part of the ENP120 – Energy Technology course.

The objective is to design a reliable microgrid capable of supplying:

- A continuous 1 MW data center load  
- Residential electricity demand  
- Local industry and infrastructure  
- Electric vehicle charging  

The system is simulated hourly over a full year using meteorological data and engineering-based load models.

---

## Modelling Approach

The system is implemented as an isolated microgrid where electricity supply and demand must be balanced at every timestep.

At each timestep:

- If generation exceeds demand → battery charges  
- If demand exceeds generation → battery discharges  
- If storage is full → surplus energy is curtailed  
- If storage is empty → unmet load occurs  

This allows evaluation of both normal operation and extreme scenarios.

---

## Key Features

- Wind data from MET Norway (Frost API)  
- Solar data from Open-Meteo API  
- Modular API structure (base_api)  
- Hourly energy balance simulation  
- Battery storage modelling (energy and power limits)  
- 48-hour Dunkelflaute stress test  
- District heating impact analysis  
- KPI export to CSV  

---

## Project Structure

UTSIRA_PROJECT/  
│  
├── api/  
│   ├── base_api.py  
│   ├── frost_api.py  
│   └── openmeteo_api.py  
│  
├── model/  
│   ├── generation_model.py  
│   ├── load_model.py  
│   └── battery_model.py  
│  
├── utils/  
│   ├── plotting.py  
│   └── kpi_export.py  
│  
├── data/  
│   └── The G-Nexus Data Center_Updated (1).csv  
│  
├── outputs/  
│   ├── *.png  
│   └── kpi_summary.csv  
│  
├── report/  
│   ├── ENP120_Utsira_Project_Group16.pdf  
│   └── ENP120-Presentation.pptx (Initial idea)
├── main.py  
├── requirements.txt  
└── README.md  

---

## How to Run

1. Create and activate a virtual environment:

python -m venv .venv  
source .venv/bin/activate  

2. Install dependencies:

pip install -r requirements.txt  

3. Create a `.env` file:

FROST_CLIENT_ID=your_api_key_here  

4. Run the simulation:

python main.py  

---

## Outputs

The simulation generates:

- Time series plots (generation, load, battery SOC)  
- Monthly energy summaries  
- Battery charge/discharge behaviour  
- Dunkelflaute stress test results  
- District heating impact analysis  
- KPI summary (CSV)  

All outputs are saved in:

outputs/  

---

## System Configuration

- Wind capacity: 5 MW  
- Solar capacity: 1 MW  
- Battery storage: 130 MWh / 5 MW  
- Data center load: 1 MW  
- EV charging: 200 chargers  

---

## Dunkelflaute Scenario

A 48-hour low-generation scenario is simulated to evaluate system robustness.

The battery system is able to maintain supply during this period when initialized at a sufficiently high state of charge. This confirms that the system meets the required reliability criterion under the defined assumptions.

---

## District Heating

Waste heat from the data center is used to reduce electrical heating demand.

This reduces peak load during winter and improves overall system efficiency.

---

## Course Information

Course: ENP120 – Energy Technology  
Institution: University of Stavanger  
Semester: Spring 2026  

---

## Author

André Hetlevik