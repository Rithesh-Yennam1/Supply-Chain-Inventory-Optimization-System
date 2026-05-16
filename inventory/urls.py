from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify_email'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Inventory
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Sales
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/add/', views.sale_add, name='sale_add'),

    # Forecasting
    path('forecasts/', views.forecast_list, name='forecast_list'),
    path('forecasts/run/', views.run_forecast_view, name='run_forecast'),

    # Alerts
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:pk>/resolve/', views.resolve_alert, name='resolve_alert'),

    # Reports & Analytics
    path('reports/', views.report_view, name='report'),
    path('reports/category/', views.category_analytics, name='category_analytics'),
    path('reports/profit-loss/', views.profit_loss_report, name='profit_loss'),

    # Exports
    path('export/sales/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('export/sales/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('export/products/excel/', views.export_products_excel, name='export_products_excel'),
    path('export/products/pdf/', views.export_products_pdf, name='export_products_pdf'),
    path('export/profit-loss/excel/', views.export_profit_loss_excel, name='export_pl_excel'),

    # Data Engineering
    path('etl/', views.etl_dashboard, name='etl_dashboard'),
    path('etl/run/', views.run_etl, name='run_etl'),
    path('etl/import/', views.data_import_view, name='data_import'),

    # Data Mining
    path('mining/clustering/', views.clustering_view, name='clustering'),
    path('mining/association-rules/', views.association_rules_view, name='association_rules'),
    path('mining/anomaly/', views.anomaly_view, name='anomaly'),
    path('mining/run/', views.run_mining, name='run_mining'),
]
