# **Trading System**
*a fun Python wrapper to build trading bots on multiple exchanges*

| Badge | Description |
|-------|-------------|
| ![Python](https://img.shields.io/badge/Python-3.12-blue) | Python 3.12 |
| ![TWS](https://img.shields.io/badge/TWS-Latest-blue) | Trader Workstation (Latest) |

## **Overview**
This project aims to build an "all-in-one" platform to deploy trading algorithms on a variety of trading venues, in a smooth and highly customizable fashion, using OOP to define the most important building blocks of a trading application.

## **Repository Structure**

- **`.config/`**
  - Contains configuration files (e.g., API keys, environment variables, yaml parameter files).

- **`data/`**
  - Stores datasets for research and analysis.
    
- **`log/`**
  - Stores logging information of various components of the program, including the main thread, strategies and unit tests.

- **`src/`**
  - Main source code for the hedge fund library, organized into modules.
  - Subfolders:
    - **`Agents/`**: Programs with no write permission on other components, meant to run computations of distinct processes, useful for risk, pnl attribution and API for communication with GUIs.
    - **`Client/`**: Abstract classes with read/write permissions that define structure around specific portions of the program, such as trading strategies and unittests.
    - **`Engine/`**: Central piece of the program which handles the coordination of threads, initialization of Clients & Gateways, user input, etc.
    - **`Gateway/`**: Interfaces meant to streamline communication with various exchanges.
    - **`Strategy/`**: Classes meant to encapsulate trading strategies.
    - **`trading/`**: Objects, data and functions used specifically within the context of trading which work on all Gateways (with some exceptions).
    - **`utils/`**: Redundant functions and data used parsimoniously throughout the program.

- **`tests/`**
  - Unit tests for validating the functionality and accuracy of the codebase.

## **Key Files**

- **`src/main.py`**: Entry point for running the repository. Use this to execute core workflows like data ingestion, backtesting, or strategy evaluation.
- **`README.md`**: This documentation file.

## **Workflow**

The project workflow follows these key steps:

## Configuring the system
### 1. General configuration
  - Modify **`.config/client_params.yaml`** to configure strategies being run, a *client* will be activated if a key holding the same name as the `NAME` class member of a Client subclass.
  - Modify **`.config/gateway_params.yaml`** to configure gateways being used, a *gateway* will be activated if a key holding the same name as the `NAME` class member of a Gateway subclass.
  - Modify **`.config/logging_config.yaml`** to configure logging mechanism being used (optional).
  - Create and configure **`.config/.env`** to add any API Key or sensitive information.

## Running the System
1. Ensure configuration is done.
2. Create virtual environment `python -m venv venv && .\venv\Scripts\activate`
3. Familiarize oneself with program commands by running `python main.py --help`
4. Run the program
