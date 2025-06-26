# Portfolio Optimizer (Code Sample)

This is a standalone code sample extracted from a larger proprietary project developed as part of a fund administration platform at Black Jade Capital. It is intended for **demonstration purposes only** and showcases select technical components used in portfolio performance analysis.

> Note: This repo contains representative backend components from a larger internal project. It is **not runnable out of the box**, but includes key logic and example outputs to demonstrate project scope and technical design.

---

## Overview

This tool enables users to:

- Input investment portfolios from **Interactive Brokers** or **Charles Schwab**
- Fetch **real-time and historical price data** for portfolio positions
- Simulate performance across different **market volatility periods** or **relative all-time highs**
- Calculate **accumulated options premiums** using imported trade data for custom time ranges
- Generate detailed **performance reports** in PDF format

---

## Features

- Real-time and historical data fetching via **Yahoo Finance**
- Portfolio importation and trade parsing (IBKR/Schwab)
- PDF generation for performance summaries and historical simulations

---

## Tech Stack

- **Python**, **NumPy**, and **pandas** for data modeling
- **PostgreSQL** for structured trade and position storage
- **Django** (backend) and **React** (frontend) for web deployment
- **jsPDF** for client-side PDF report generation

---

## Demo Output

- PDF Report: Please see within the examples/ folder for samples of the generated PDF report
- Frontend Display: Please refer to the frontend_demo/ folder for samples of the front end display for Trade Analysis, Portfolio Analysis, and Portfolio ATH Analysis

---
## Note

This repository contains a simplified version of core functionalities extracted from a broader internal system.  
All data has been **anonymized**, and no proprietary logic or account-specific integrations are included.

## Architecture Note

In the full project implementation at Black Jade Capital, this portfolio analysis tool operates within a full-stack web application. The actual data flow follows a structured architecture:

Frontend (React + TypeScript):
Sends API requests to specific backend endpoints such as:
  
- /admin-investor-performance
- /admin-trade-analysis
- /admin-portfolio-ath
  
Backend View Layer (Django Views):
- Endpoints like /admin-investor-performance are routed through AdminView classes, which handle authentication and request validation.

Service Layer (AdminService):
- The views delegate business logic to service functions like get_investor_performance() or calculate_portfolio_exposures(), defined in the AdminService class.

Utility Layer (trade_analysis_utils.py):
- These service functions call into modular backend utilities such as calculate_what_if_exposure, calculate_options_premiums, or calculate_all_portfolio_aths, which process data and return formatted results.

Response Handling:
- Results are returned to the frontend as structured JSON and used to render visual dashboards or generate downloadable PDFs.

This repository isolates the core computational logic (trade_analysis_utils.py) and selected frontend display components (frontend_demo/) for demonstration purposes only. It is not runnable out of the box, but illustrates key data transformations and architecture from the broader internal system.

