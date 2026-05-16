# Supply Chain & Inventory Optimization System

A full-stack web application built with **Django**, **MySQL**, **Machine Learning**, and **Data Engineering** tools to help businesses forecast demand, manage inventory, detect anomalies, and analyze sales performance.

---

## Features

### Inventory Management
- Add, edit, delete products with stock tracking
- Low stock detection with automatic reorder alerts
- Multi-warehouse support

### Sales Management
- Record daily sales with automatic stock deduction
- Sales history with date filtering

### Demand Forecasting (ML)
- Linear Regression and Random Forest models
- Auto-selects best model based on available data
- 30-day ahead demand predictions

### Data Engineering (ETL)
- Nightly scheduled ETL pipelines using APScheduler
- Daily sales data warehouse aggregation
- CSV / Excel bulk data import
- Full ETL run logs with status tracking

### Data Mining
- **K-Means Clustering** — segments products into performance groups
- **Apriori Association Rules** — finds products frequently sold together
- **Isolation Forest Anomaly Detection** — detects unusual sales patterns

### Analytics & Reports
- Interactive **Plotly** charts (revenue trend, category pie, top products)
- **Date range filtering** on all reports
- **Category Analytics** — revenue and units by category
- **Profit & Loss Report** — monthly revenue vs cost vs profit
- Export reports to **Excel** and **PDF**

### Authentication
- User registration with **email verification**
- Secure login / logout
- Django admin panel

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 |
| Database | MySQL |
| ML / Data | scikit-learn, statsmodels, mlxtend, pandas, numpy |
| Scheduling | APScheduler |
| Visualization | Plotly, Chart.js |
| Export | ReportLab (PDF), openpyxl (Excel) |
| Frontend | Bootstrap 5, Bootstrap Icons |
| Language | Python 3.11 |

---

## Project Structure

```
inventary/
├── inventory/
│   ├── models.py          # All database models
│   ├── views.py           # All views
│   ├── urls.py            # URL routing
│   ├── forms.py           # Django forms
│   ├── ml_forecast.py     # ML forecasting logic
│   ├── etl_pipeline.py    # ETL + data mining pipelines
│   ├── data_import.py     # CSV/Excel import utility
│   ├── export_utils.py    # PDF/Excel export utility
│   ├── scheduler.py       # APScheduler nightly jobs
│   └── admin.py           # Django admin config
├── supply_chain/
│   ├── settings.py        # Project settings
│   └── urls.py            # Root URL config
├── templates/             # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── auth/
│   ├── inventory/
│   ├── sales/
│   ├── forecast/
│   ├── alerts/
│   ├── reports/
│   ├── engineering/
│   └── mining/
├── sample_products.csv    # Sample data for import
├── sample_sales.csv       # Sample data for import
├── requirements.txt
└── manage.py
```

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/supply-chain-system.git
cd supply-chain-system
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure MySQL database
Create a database in MySQL:
```sql
CREATE DATABASE supply_chain_db CHARACTER SET utf8mb4;
```

Update `supply_chain/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'supply_chain_db',
        'USER': 'root',
        'PASSWORD': 'your_mysql_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Configure Gmail (for email verification)
Update `supply_chain/settings.py`:
```python
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_gmail_app_password'
```
> Get App Password: Google Account → Security → 2-Step Verification → App Passwords

### 6. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create superuser
```bash
python manage.py createsuperuser
```

### 8. Run the server
```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

---

## Sample Data

Import sample data to get started quickly:

1. Go to `http://127.0.0.1:8000/etl/import/`
2. Select **Products** → upload `sample_products.csv`
3. Select **Sales** → upload `sample_sales.csv`
4. Go to dashboard → click **Run ETL Now** then **Run Mining**

---

## Pages & URLs

| Page | URL |
|---|---|
| Dashboard | `/` |
| Products | `/products/` |
| Sales | `/sales/` |
| Forecasts | `/forecasts/` |
| Reorder Alerts | `/alerts/` |
| Reports | `/reports/` |
| Category Analytics | `/reports/category/` |
| Profit & Loss | `/reports/profit-loss/` |
| ETL Dashboard | `/etl/` |
| Data Import | `/etl/import/` |
| Clustering | `/mining/clustering/` |
| Association Rules | `/mining/association-rules/` |
| Anomaly Detection | `/mining/anomaly/` |
| Admin Panel | `/admin/` |

---

## Screenshots

> Add screenshots here after running the project.

---

## License

This project is for educational purposes.
