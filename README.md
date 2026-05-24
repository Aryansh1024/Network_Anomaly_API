# Network Anomaly Detection API

A robust backend REST API built with FastAPI that extracts network telemetry from RRD (Round Robin Database) files and performs statistical anomaly detection.

## Features
* **Dynamic Data Extraction:** Interfaces with native `rrdtool` binaries to extract time-series network data.
* **Statistical Anomaly Detection:** Implements multiple algorithms to identify network issues:
  * **Z-Score:** Detects extreme deviations from the mean.
  * **IQR (Interquartile Range):** Identifies outliers outside normal operating bands.
  * **Trend Analysis:** Flags sustained upward or downward drift using linear regression.
  * **Flatline Detection:** Identifies frozen sensors or dropped interfaces via zero-variance checks.
* **Interactive Documentation:** Auto-generated Swagger UI for easy endpoint testing.

## Tech Stack
* **Framework:** FastAPI / Uvicorn
* **Data Processing:** Pandas, NumPy
* **Data Source:** RRDtool

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YourUsername/Network_Anomaly_API.git](https://github.com/YourUsername/Network_Anomaly_API.git)
   cd Network_Anomaly_API