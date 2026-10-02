# mapadotacji.gov.pl ETL Pipeline & Scraper

An advanced, fault tolerant ETL pipeline designed to asynchronously extract and process data regarding EU funded projects in Poland.

This project is engineered with a strong focus on resilience, network stability and data integrity.

## Table of Contents
- [General Information](#general-information)
- [Technologies Used](#technologies-used)
- [Features](#features)
- [Setup](#setup)
- [Running the Scraper](#running-the-scraper)

## General Information
Extracting large datasets from public infrastructure can lead to bottlenecks, IP bans and unpredictable server downtimes. This project is a robust ETL (Extracl, Transform, Load) pipeline designed to survive network chaos.

## Technologies Used
* Python 3.10+
* HTTPX with HTTP/2 support
* BeautifulSoup4
* Pydantic
* Threading
* concurrent.futures

## Features
* Monitoring of continuous IO errors across all worker threads. Suspension of the entire application during server outages.
* Safely writing parsed records to a .jsonl file concurrently without data loss nor memory overhead.
* Implementing both linear and exponential backoff with delay jitter to mitigate 429 and 503 responses.
* Tracking of visited URLs and search pages with the purpose of resuming exactly where we left off in case of interruption.
* Utilizing Pydantic models to guarantee data structure consistency before committing record to storage.

## Setup
Clone the repository and prepare the virtual environment:
```
git clone https://github.com/czekajmic/portfolio-web-scraper/
cd portfolio-web-scraper
python3 -m venv venv
```
Activate the virtual environment:

On Linux/macOS:
```
source venv/bin/activate
```
On Windows:
```
venv/Scripts/activate
```

Upgrade pip and install dependencies:
```
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Scraper
To run the pipeline and begin extraction, ensure your virtual environment is active, then run the main module from the root directory:
```
python3 -m src.main
```
