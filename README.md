# Pricing Optimization & A/B Testing Dashboard

An end-to-end pricing analytics project built with Python and JavaScript.

This project analyzes retail bike transaction data, simulates pricing optimization strategies, validates them using A/B testing, and visualizes the results through an interactive dashboard.

---

## Project Overview

The goal of this project is to build a decision-ready pricing analytics system that helps identify revenue optimization opportunities across different product categories.

The system includes:

- Business performance analysis
- Pricing optimization simulation
- Scenario-based pricing evaluation
- Statistical A/B testing validation
- Interactive dashboard visualization

---

## Features

### 1. Business Analysis
Analyzes overall business performance including:

- Total revenue
- Transaction volume
- Revenue quality metrics
- Monthly seasonality and momentum
- Price tier comparisons
- Category dependence analysis

### 2. Pricing Optimization
Simulates optimal pricing strategies for each product category.

Outputs include:

- Baseline revenue
- Optimal price recommendation
- Expected revenue uplift

### 3. Scenario Analysis
Tests multiple pricing tiers:

- Low price
- Mid price
- High price

The system evaluates revenue sensitivity and generates pricing recommendations.

### 4. A/B Testing Framework
Validates pricing strategies statistically using simulated control and treatment groups.

Metrics include:

- Revenue uplift %
- p-value significance testing
- Deployment recommendations

---

## Dashboard

The frontend dashboard visualizes:

- Monthly revenue trends
- Baseline vs optimized revenue
- Pricing uplift by category
- A/B testing results and recommendations

Built using:

- HTML
- CSS
- JavaScript
- Chart.js

---

## Tech Stack

### Backend
- Python
- Pandas
- NumPy
- SciPy

### Frontend
- HTML
- CSS
- JavaScript
- Chart.js

---

## Project Structure

```bash
hotel-mvp/
│
├── data_raw/               # Raw retail transaction data
├── data_out/               # Processed JSON outputs
├── src/                    # Python analytics scripts
├── frontend/               # Dashboard frontend
│
├── business_analysis.py
├── pricing_optimization.py
├── pricing_ab_test.py
└── results.json
