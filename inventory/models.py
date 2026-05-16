from django.db import models
from django.contrib.auth.models import User
import uuid


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_token')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.username}"


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    stock = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    reorder_threshold = models.IntegerField(default=10)
    warehouse = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.stock <= self.reorder_threshold


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity_sold = models.IntegerField()
    sale_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.quantity_sold} on {self.sale_date}"


class Forecast(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecasts')
    predicted_demand = models.FloatField()
    forecast_date = models.DateField()
    model_used = models.CharField(max_length=50, default='LinearRegression')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.predicted_demand} ({self.forecast_date})"


class ReorderAlert(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('resolved', 'Resolved')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    current_stock = models.IntegerField()
    predicted_demand = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert: {self.product.name} (Stock: {self.current_stock})"


# ─── Data Engineering Models ──────────────────────────────────────────────────

class ETLLog(models.Model):
    STATUS_CHOICES = [('success', 'Success'), ('failed', 'Failed'), ('running', 'Running')]
    pipeline_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    records_processed = models.IntegerField(default=0)
    message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.pipeline_name} - {self.status} ({self.started_at.date()})"


class DailySalesSummary(models.Model):
    """Data warehouse table - aggregated daily sales"""
    date = models.DateField(unique=True)
    total_quantity = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unique_products = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary {self.date}"


class ProductCluster(models.Model):
    """K-Means clustering results"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='cluster')
    cluster_id = models.IntegerField()
    total_sales = models.FloatField(default=0)
    avg_quantity = models.FloatField(default=0)
    sales_frequency = models.FloatField(default=0)
    cluster_label = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - Cluster {self.cluster_id}"


class AssociationRule(models.Model):
    """Apriori association rules"""
    antecedent = models.CharField(max_length=255)  # if product A
    consequent = models.CharField(max_length=255)  # then product B
    support = models.FloatField()
    confidence = models.FloatField()
    lift = models.FloatField()
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.antecedent} → {self.consequent} (lift={self.lift:.2f})"


class AnomalyRecord(models.Model):
    """Isolation Forest anomaly detection results"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='anomalies')
    sale_date = models.DateField()
    quantity_sold = models.IntegerField()
    anomaly_score = models.FloatField()
    is_anomaly = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{'ANOMALY' if self.is_anomaly else 'Normal'}: {self.product.name} on {self.sale_date}"
