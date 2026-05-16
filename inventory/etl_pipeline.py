import pandas as pd
import numpy as np
from datetime import datetime, date
from django.utils import timezone
from django.db.models import Sum, Count, Avg


def run_daily_summary_etl():
    """ETL: Extract sales, Transform to daily summaries, Load into DailySalesSummary"""
    from .models import Sale, DailySalesSummary, ETLLog, Product

    log = ETLLog.objects.create(pipeline_name='DailySalesSummary ETL', status='running')
    try:
        # Extract
        sales = Sale.objects.select_related('product').values(
            'sale_date', 'quantity_sold', 'product__price'
        )
        if not sales:
            log.status = 'success'
            log.message = 'No sales data to process.'
            log.finished_at = timezone.now()
            log.save()
            return

        # Transform
        df = pd.DataFrame(list(sales))
        df['revenue'] = df['quantity_sold'] * df['product__price'].astype(float)
        daily = df.groupby('sale_date').agg(
            total_quantity=('quantity_sold', 'sum'),
            total_revenue=('revenue', 'sum'),
            unique_products=('sale_date', 'count')
        ).reset_index()

        # Load
        count = 0
        for _, row in daily.iterrows():
            DailySalesSummary.objects.update_or_create(
                date=row['sale_date'],
                defaults={
                    'total_quantity': int(row['total_quantity']),
                    'total_revenue': round(row['total_revenue'], 2),
                    'unique_products': int(row['unique_products']),
                }
            )
            count += 1

        log.status = 'success'
        log.records_processed = count
        log.message = f'Processed {count} daily summaries.'
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise


def run_clustering_etl():
    """ETL: K-Means clustering on products based on sales behavior"""
    from .models import Sale, Product, ProductCluster, ETLLog
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    log = ETLLog.objects.create(pipeline_name='Product Clustering ETL', status='running')
    try:
        sales = Sale.objects.values('product').annotate(
            total_sales=Sum('quantity_sold'),
            avg_quantity=Avg('quantity_sold'),
            frequency=Count('id')
        )
        if sales.count() < 3:
            log.status = 'failed'
            log.message = 'Need at least 3 products with sales for clustering.'
            log.finished_at = timezone.now()
            log.save()
            return

        df = pd.DataFrame(list(sales))
        features = df[['total_sales', 'avg_quantity', 'frequency']].fillna(0)

        scaler = StandardScaler()
        scaled = scaler.fit_transform(features)

        n_clusters = min(4, len(df))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(scaled)

        cluster_labels = {0: 'Low Performer', 1: 'Medium Performer', 2: 'High Performer', 3: 'Top Performer'}

        count = 0
        for _, row in df.iterrows():
            product = Product.objects.get(pk=row['product'])
            ProductCluster.objects.update_or_create(
                product=product,
                defaults={
                    'cluster_id': int(row['cluster']),
                    'total_sales': float(row['total_sales']),
                    'avg_quantity': float(row['avg_quantity']),
                    'sales_frequency': float(row['frequency']),
                    'cluster_label': cluster_labels.get(int(row['cluster']), f'Cluster {row["cluster"]}'),
                }
            )
            count += 1

        log.status = 'success'
        log.records_processed = count
        log.message = f'Clustered {count} products into {n_clusters} groups.'
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise


def run_association_rules_etl():
    """ETL: Apriori association rules on products sold on same date"""
    from .models import Sale, AssociationRule, ETLLog
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder

    log = ETLLog.objects.create(pipeline_name='Association Rules ETL', status='running')
    try:
        sales = Sale.objects.values('sale_date', 'product__name')
        if not sales:
            log.status = 'failed'
            log.message = 'No sales data available.'
            log.finished_at = timezone.now()
            log.save()
            return

        df = pd.DataFrame(list(sales))
        # Group products sold on same date as transactions
        transactions = df.groupby('sale_date')['product__name'].apply(list).tolist()

        if len(transactions) < 2:
            log.status = 'failed'
            log.message = 'Need at least 2 transaction dates for association rules.'
            log.finished_at = timezone.now()
            log.save()
            return

        te = TransactionEncoder()
        te_array = te.fit_transform(transactions)
        basket_df = pd.DataFrame(te_array, columns=te.columns_)

        frequent = apriori(basket_df, min_support=0.1, use_colnames=True)
        if frequent.empty:
            log.status = 'success'
            log.message = 'No frequent itemsets found. Add more sales data.'
            log.finished_at = timezone.now()
            log.save()
            return

        rules = association_rules(frequent, metric='lift', min_threshold=1.0, num_itemsets=len(frequent))

        AssociationRule.objects.all().delete()
        count = 0
        for _, rule in rules.iterrows():
            AssociationRule.objects.create(
                antecedent=', '.join(list(rule['antecedents'])),
                consequent=', '.join(list(rule['consequents'])),
                support=round(float(rule['support']), 4),
                confidence=round(float(rule['confidence']), 4),
                lift=round(float(rule['lift']), 4),
            )
            count += 1

        log.status = 'success'
        log.records_processed = count
        log.message = f'Generated {count} association rules.'
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise


def run_anomaly_detection_etl():
    """ETL: Isolation Forest anomaly detection on sales data"""
    from .models import Sale, AnomalyRecord, ETLLog
    from sklearn.ensemble import IsolationForest

    log = ETLLog.objects.create(pipeline_name='Anomaly Detection ETL', status='running')
    try:
        sales = Sale.objects.select_related('product').values(
            'id', 'product', 'product__name', 'sale_date', 'quantity_sold'
        )
        if not sales or len(sales) < 5:
            log.status = 'failed'
            log.message = 'Need at least 5 sales records for anomaly detection.'
            log.finished_at = timezone.now()
            log.save()
            return

        df = pd.DataFrame(list(sales))
        df['day_of_week'] = pd.to_datetime(df['sale_date']).dt.dayofweek
        df['month'] = pd.to_datetime(df['sale_date']).dt.month

        features = df[['quantity_sold', 'day_of_week', 'month']]
        model = IsolationForest(contamination=0.1, random_state=42)
        df['anomaly'] = model.fit_predict(features)
        df['score'] = model.score_samples(features)

        AnomalyRecord.objects.all().delete()
        count = 0
        for _, row in df.iterrows():
            from .models import Product
            product = Product.objects.get(pk=row['product'])
            AnomalyRecord.objects.create(
                product=product,
                sale_date=row['sale_date'],
                quantity_sold=int(row['quantity_sold']),
                anomaly_score=round(float(row['score']), 4),
                is_anomaly=(row['anomaly'] == -1),
            )
            count += 1

        anomaly_count = df[df['anomaly'] == -1].shape[0]
        log.status = 'success'
        log.records_processed = count
        log.message = f'Analyzed {count} records. Found {anomaly_count} anomalies.'
        log.finished_at = timezone.now()
        log.save()

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        raise


def run_all_pipelines():
    """Run all ETL pipelines in sequence"""
    run_daily_summary_etl()
    run_clustering_etl()
    run_association_rules_etl()
    run_anomaly_detection_etl()
