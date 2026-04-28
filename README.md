# G-Nexus Utsira Project – Energy System Simulation

## Overview
This project models a 100% renewable energy system for the island of Utsira, Norway, as part of the ENP120 – Energy Technology course.

The objective is to design a reliable, carbon-neutral system capable of supplying:
- A 1 MW Google data center
- Residential demand
- Local industry and infrastructure
- Electric vehicle charging

The system is simulated hourly over a full year using real weather data.

---

## Key Features

- Wind data from MET Norway (Frost API)
- Solar data from Open-Meteo API
- Modular API structure (with base_api)
- Hourly energy balance simulation
- Battery storage modeling (energy and power limits)
- 48-hour Dunkelflaute stress test (no generation)
- District heating impact analysis
- KPI export to CSV

---

## Project Structure

UTSIRA_PROJECT/
│
├── api/
│   ├── __init__.py
│   ├── base_api.py
│   ├── frost_api.py
│   ├── openmeteo_api.py
│   └── elhub_api.py
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
│   └── ENP120_Utsira_Project_Group16.pdf
│
├── main.py
├── requirements.txt
├── .env
└── README.md

---

## How to Run

1. (Recommended) Create and activate virtual environment:
python -m venv .venv  
source .venv/bin/activate  

2. Install dependencies:
pip install -r requirements.txt

3. Create a .env file:
FROST_CLIENT_ID=your_api_key_here

4. Run the simulation:
python main.py

---

## Outputs

The simulation generates:

- Time series plots (load, generation, battery SOC)
- Monthly energy summaries
- Battery charge/discharge behavior
- Dunkelflaute stress test results
- District heating impact plot
- KPI summary (CSV)

All outputs are saved in:
outputs/

---

## System Configuration

- Wind capacity: 5 MW
- Solar capacity: 1 MW
- Battery storage: 80 MWh / 5 MW
- Data center load: 1 MW
- EV charging: 200 chargers

---

## Dunkelflaute Scenario

A 48-hour period with no wind and no solar generation is simulated.

The battery must supply the system alone during this period.  
Results show that storage alone is insufficient to guarantee full reliability, highlighting the need for additional flexibility or backup solutions.

---

## District Heating

Waste heat from the data center is used to reduce winter electrical demand.

This lowers peak load significantly and improves overall system efficiency.

---

## Course Information

Course: ENP120 – Energy Technology  
Institution: University of Stavanger  
Semester: Spring 2026  

---

## Author

André Hetlevik