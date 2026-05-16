from django.contrib import admin
from .models import Product, Sale, Forecast, ReorderAlert

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'stock', 'price', 'reorder_threshold', 'warehouse']
    search_fields = ['name', 'category']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity_sold', 'sale_date']
    list_filter = ['sale_date']

@admin.register(Forecast)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ['product', 'predicted_demand', 'forecast_date', 'model_used']

@admin.register(ReorderAlert)
class ReorderAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'current_stock', 'predicted_demand', 'status', 'created_at']
    list_filter = ['status']
