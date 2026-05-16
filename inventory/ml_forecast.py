import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta


def get_sales_dataframe(product):
    sales = product.sales.order_by('sale_date').values('sale_date', 'quantity_sold')
    if not sales:
        return None
    df = pd.DataFrame(list(sales))
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df['day_index'] = (df['sale_date'] - df['sale_date'].min()).dt.days
    return df


def forecast_linear(product, days_ahead=30):
    df = get_sales_dataframe(product)
    if df is None or len(df) < 2:
        return None, 'LinearRegression'
    X = df[['day_index']]
    y = df['quantity_sold']
    model = LinearRegression()
    model.fit(X, y)
    next_day = df['day_index'].max() + days_ahead
    prediction = model.predict([[next_day]])[0]
    return max(0, round(prediction, 2)), 'LinearRegression'


def forecast_random_forest(product, days_ahead=30):
    df = get_sales_dataframe(product)
    if df is None or len(df) < 5:
        return forecast_linear(product, days_ahead)
    X = df[['day_index']]
    y = df['quantity_sold']
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    next_day = df['day_index'].max() + days_ahead
    prediction = model.predict([[next_day]])[0]
    return max(0, round(prediction, 2)), 'RandomForest'


def run_forecast(product, days_ahead=30):
    df = get_sales_dataframe(product)
    if df is None:
        return None, 'NoData'
    if len(df) >= 5:
        return forecast_random_forest(product, days_ahead)
    return forecast_linear(product, days_ahead)
