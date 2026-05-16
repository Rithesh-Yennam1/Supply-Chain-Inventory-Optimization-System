import pandas as pd
from datetime import datetime


def import_products_from_file(file):
    """
    Expected columns: name, category, stock, price, reorder_threshold, warehouse
    """
    from .models import Product, ETLLog
    from django.utils import timezone

    log = ETLLog.objects.create(pipeline_name='Product Import', status='running')
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        required = ['name', 'stock', 'price']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        count = 0
        for _, row in df.iterrows():
            Product.objects.update_or_create(
                name=str(row['name']).strip(),
                defaults={
                    'category': str(row.get('category', '')),
                    'stock': int(row.get('stock', 0)),
                    'price': float(row.get('price', 0)),
                    'reorder_threshold': int(row.get('reorder_threshold', 10)),
                    'warehouse': str(row.get('warehouse', '')),
                }
            )
            count += 1

        log.status = 'success'
        log.records_processed = count
        log.message = f'Imported {count} products.'
        log.finished_at = timezone.now()
        log.save()
        return count, None

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        return 0, str(e)


def import_sales_from_file(file):
    """
    Expected columns: product_name, quantity_sold, sale_date
    """
    from .models import Product, Sale, ETLLog
    from django.utils import timezone

    log = ETLLog.objects.create(pipeline_name='Sales Import', status='running')
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        required = ['product_name', 'quantity_sold', 'sale_date']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        count, skipped = 0, 0
        for _, row in df.iterrows():
            try:
                product = Product.objects.get(name__iexact=str(row['product_name']).strip())
                sale_date = pd.to_datetime(row['sale_date']).date()
                Sale.objects.create(
                    product=product,
                    quantity_sold=int(row['quantity_sold']),
                    sale_date=sale_date,
                )
                count += 1
            except Product.DoesNotExist:
                skipped += 1

        log.status = 'success'
        log.records_processed = count
        log.message = f'Imported {count} sales. Skipped {skipped} (product not found).'
        log.finished_at = timezone.now()
        log.save()
        return count, None

    except Exception as e:
        log.status = 'failed'
        log.message = str(e)
        log.finished_at = timezone.now()
        log.save()
        return 0, str(e)
