from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count, F, ExpressionWrapper, DecimalField
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
import json
from .models import (Product, Sale, Forecast, ReorderAlert, EmailVerificationToken,
                     ETLLog, DailySalesSummary, ProductCluster, AssociationRule, AnomalyRecord)
from .forms import RegisterForm, LoginForm, ProductForm, SaleForm
from .ml_forecast import run_forecast


# ─── Auth ─────────────────────────────────────────────────────────────────────

def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        token_obj = EmailVerificationToken.objects.create(user=user)
        verify_url = request.build_absolute_uri(f'/verify-email/{token_obj.token}/')
        send_mail(
            subject='Verify your email - Supply Chain System',
            message=f'Hi {user.username},\n\nClick the link below to verify your email:\n{verify_url}\n\nIf you did not register, ignore this email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        messages.success(request, 'Registration successful! Please check your email to verify your account.')
        return redirect('login')
    return render(request, 'auth/register.html', {'form': form})


def verify_email_view(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)
    user = token_obj.user
    if not user.is_active:
        user.is_active = True
        user.save()
        token_obj.delete()
        messages.success(request, 'Email verified successfully! You can now login.')
    else:
        messages.info(request, 'Email already verified.')
    return redirect('login')


def login_view(request):
    form = LoginForm(request, request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
        else:
            username = request.POST.get('username')
            from django.contrib.auth.models import User as AuthUser
            try:
                u = AuthUser.objects.get(username=username)
                if not u.is_active:
                    messages.error(request, 'Please verify your email before logging in.')
                    return render(request, 'auth/login.html', {'form': form})
            except AuthUser.DoesNotExist:
                pass
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    total_products = Product.objects.count()
    low_stock = Product.objects.filter(stock__lte=10).count()
    pending_alerts = ReorderAlert.objects.filter(status='pending').count()
    total_sales = Sale.objects.aggregate(total=Sum('quantity_sold'))['total'] or 0
    recent_alerts = ReorderAlert.objects.filter(status='pending').select_related('product')[:5]
    low_stock_products = Product.objects.filter(stock__lte=10)[:5]
    anomaly_count = AnomalyRecord.objects.filter(is_anomaly=True).count()
    total_revenue = Sale.objects.aggregate(
        rev=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField()))
    )['rev'] or 0
    context = {
        'total_products': total_products,
        'low_stock': low_stock,
        'pending_alerts': pending_alerts,
        'total_sales': total_sales,
        'recent_alerts': recent_alerts,
        'low_stock_products': low_stock_products,
        'anomaly_count': anomaly_count,
        'total_revenue': round(total_revenue, 2),
    }
    return render(request, 'dashboard.html', context)


# ─── Inventory ────────────────────────────────────────────────────────────────

@login_required
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'inventory/product_list.html', {'products': products})


@login_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product added successfully.')
        return redirect('product_list')
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('product_list')
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product'})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


# ─── Sales ────────────────────────────────────────────────────────────────────

@login_required
def sale_list(request):
    sales = Sale.objects.select_related('product').order_by('-sale_date')
    return render(request, 'sales/sale_list.html', {'sales': sales})


@login_required
def sale_add(request):
    form = SaleForm(request.POST or None)
    if form.is_valid():
        sale = form.save()
        product = sale.product
        product.stock = max(0, product.stock - sale.quantity_sold)
        product.save()
        messages.success(request, 'Sale recorded.')
        return redirect('sale_list')
    return render(request, 'sales/sale_form.html', {'form': form})


# ─── Forecasting ──────────────────────────────────────────────────────────────

@login_required
def forecast_list(request):
    forecasts = Forecast.objects.select_related('product').order_by('-created_at')
    return render(request, 'forecast/forecast_list.html', {'forecasts': forecasts})


@login_required
def run_forecast_view(request):
    products = Product.objects.all()
    generated = 0
    for product in products:
        predicted, model_used = run_forecast(product)
        if predicted is not None:
            Forecast.objects.create(
                product=product,
                predicted_demand=predicted,
                forecast_date=date.today() + timedelta(days=30),
                model_used=model_used,
            )
            if product.stock < predicted:
                ReorderAlert.objects.get_or_create(
                    product=product,
                    status='pending',
                    defaults={'current_stock': product.stock, 'predicted_demand': predicted}
                )
            generated += 1
    messages.success(request, f'Forecasts generated for {generated} products.')
    return redirect('forecast_list')


# ─── Reorder Alerts ───────────────────────────────────────────────────────────

@login_required
def alert_list(request):
    alerts = ReorderAlert.objects.select_related('product').order_by('-created_at')
    return render(request, 'alerts/alert_list.html', {'alerts': alerts})


@login_required
def resolve_alert(request, pk):
    alert = get_object_or_404(ReorderAlert, pk=pk)
    alert.status = 'resolved'
    alert.save()
    messages.success(request, 'Alert resolved.')
    return redirect('alert_list')


# ─── Reports & Analytics ──────────────────────────────────────────────────────

def _get_date_range(request):
    """Helper to get date range from request or default to last 90 days"""
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    try:
        from datetime import datetime
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else date.today() - timedelta(days=90)
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else date.today()
    except ValueError:
        date_from = date.today() - timedelta(days=90)
        date_to = date.today()
    return date_from, date_to


@login_required
def report_view(request):
    date_from, date_to = _get_date_range(request)
    sales_qs = Sale.objects.filter(sale_date__range=[date_from, date_to])

    # Top products
    top_products = sales_qs.values('product__name').annotate(
        total=Sum('quantity_sold')
    ).order_by('-total')[:10]

    # Monthly sales
    monthly_sales = sales_qs.extra(
        select={'month': "DATE_FORMAT(sale_date, '%%Y-%%m')"}
    ).values('month').annotate(total=Sum('quantity_sold')).order_by('month')

    # Category breakdown
    category_sales = sales_qs.values('product__category').annotate(
        total=Sum('quantity_sold'),
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField()))
    ).order_by('-total')

    # Profit & Loss
    revenue = sales_qs.aggregate(
        rev=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField()))
    )['rev'] or 0
    estimated_cost = float(revenue) * 0.6
    gross_profit = float(revenue) - estimated_cost
    profit_margin = (gross_profit / float(revenue) * 100) if revenue else 0

    # Plotly: monthly revenue line chart
    monthly_revenue = sales_qs.extra(
        select={'month': "DATE_FORMAT(sale_date, '%%Y-%%m')"}
    ).values('month').annotate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField()))
    ).order_by('month')

    context = {
        'top_products': top_products,
        'monthly_sales': monthly_sales,
        'category_sales': category_sales,
        'revenue': round(revenue, 2),
        'estimated_cost': round(estimated_cost, 2),
        'gross_profit': round(gross_profit, 2),
        'profit_margin': round(profit_margin, 2),
        'date_from': date_from,
        'date_to': date_to,
        'monthly_revenue': list(monthly_revenue),
        'top_labels': json.dumps([p['product__name'] for p in top_products]),
        'top_data': json.dumps([p['total'] for p in top_products]),
        'month_labels': json.dumps([m['month'] for m in monthly_sales]),
        'month_data': json.dumps([m['total'] for m in monthly_sales]),
        'month_revenue_labels': json.dumps([m['month'] for m in monthly_revenue]),
        'month_revenue_data': json.dumps([float(m['revenue'] or 0) for m in monthly_revenue]),
        'cat_labels': json.dumps([c['product__category'] or 'Uncategorized' for c in category_sales]),
        'cat_data': json.dumps([c['total'] for c in category_sales]),
    }
    return render(request, 'reports/report.html', context)


@login_required
def category_analytics(request):
    date_from, date_to = _get_date_range(request)
    sales_qs = Sale.objects.filter(sale_date__range=[date_from, date_to])

    category_data = sales_qs.values('product__category').annotate(
        total_qty=Sum('quantity_sold'),
        total_revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField())),
        num_products=Count('product', distinct=True),
        avg_qty=Avg('quantity_sold'),
    ).order_by('-total_revenue')

    # Per category monthly trend
    monthly_by_cat = sales_qs.extra(
        select={'month': "DATE_FORMAT(sale_date, '%%Y-%%m')"}
    ).values('month', 'product__category').annotate(
        total=Sum('quantity_sold')
    ).order_by('month')

    context = {
        'category_data': category_data,
        'monthly_by_cat': list(monthly_by_cat),
        'date_from': date_from,
        'date_to': date_to,
        'cat_labels': json.dumps([c['product__category'] or 'Uncategorized' for c in category_data]),
        'cat_revenue': json.dumps([float(c['total_revenue'] or 0) for c in category_data]),
        'cat_qty': json.dumps([c['total_qty'] for c in category_data]),
    }
    return render(request, 'reports/category_analytics.html', context)


@login_required
def profit_loss_report(request):
    date_from, date_to = _get_date_range(request)
    sales_qs = Sale.objects.filter(sale_date__range=[date_from, date_to])

    monthly = sales_qs.extra(
        select={'month': "DATE_FORMAT(sale_date, '%%Y-%%m')"}
    ).values('month').annotate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField())),
        units=Sum('quantity_sold'),
    ).order_by('month')

    pl_data = []
    for m in monthly:
        rev = float(m['revenue'] or 0)
        cost = rev * 0.6
        profit = rev - cost
        pl_data.append({
            'month': m['month'],
            'revenue': round(rev, 2),
            'cost': round(cost, 2),
            'profit': round(profit, 2),
            'margin': round((profit / rev * 100) if rev else 0, 1),
            'units': m['units'],
        })

    total_rev = sum(r['revenue'] for r in pl_data)
    total_cost = sum(r['cost'] for r in pl_data)
    total_profit = sum(r['profit'] for r in pl_data)
    total_margin = round((total_profit / total_rev * 100) if total_rev else 0, 1)

    context = {
        'pl_data': pl_data,
        'total_rev': round(total_rev, 2),
        'total_cost': round(total_cost, 2),
        'total_profit': round(total_profit, 2),
        'total_margin': total_margin,
        'date_from': date_from,
        'date_to': date_to,
        'pl_labels': json.dumps([r['month'] for r in pl_data]),
        'pl_revenue': json.dumps([r['revenue'] for r in pl_data]),
        'pl_cost': json.dumps([r['cost'] for r in pl_data]),
        'pl_profit': json.dumps([r['profit'] for r in pl_data]),
    }
    return render(request, 'reports/profit_loss.html', context)


# ─── Export Views ─────────────────────────────────────────────────────────────

@login_required
def export_sales_excel(request):
    from .export_utils import export_excel
    date_from, date_to = _get_date_range(request)
    sales = Sale.objects.filter(sale_date__range=[date_from, date_to]).select_related('product').order_by('-sale_date')
    headers = ['Product', 'Category', 'Quantity Sold', 'Sale Date', 'Revenue']
    rows = [
        [s.product.name, s.product.category, s.quantity_sold, str(s.sale_date),
         round(s.quantity_sold * float(s.product.price), 2)]
        for s in sales
    ]
    return export_excel(headers, rows, 'Sales Report', 'sales_report.xlsx')


@login_required
def export_sales_pdf(request):
    from .export_utils import export_pdf
    date_from, date_to = _get_date_range(request)
    sales = Sale.objects.filter(sale_date__range=[date_from, date_to]).select_related('product').order_by('-sale_date')
    headers = ['Product', 'Category', 'Qty Sold', 'Sale Date', 'Revenue']
    rows = [
        [s.product.name, s.product.category, s.quantity_sold, str(s.sale_date),
         f"${round(s.quantity_sold * float(s.product.price), 2)}"]
        for s in sales
    ]
    return export_pdf(f'Sales Report ({date_from} to {date_to})', headers, rows, 'sales_report.pdf')


@login_required
def export_products_excel(request):
    from .export_utils import export_excel
    products = Product.objects.all().order_by('name')
    headers = ['Name', 'Category', 'Stock', 'Price', 'Reorder Threshold', 'Warehouse', 'Status']
    rows = [
        [p.name, p.category, p.stock, float(p.price), p.reorder_threshold, p.warehouse,
         'Low Stock' if p.is_low_stock else 'In Stock']
        for p in products
    ]
    return export_excel(headers, rows, 'Products', 'products_report.xlsx')


@login_required
def export_products_pdf(request):
    from .export_utils import export_pdf
    products = Product.objects.all().order_by('name')
    headers = ['Name', 'Category', 'Stock', 'Price', 'Threshold', 'Warehouse', 'Status']
    rows = [
        [p.name, p.category, p.stock, f"${p.price}", p.reorder_threshold, p.warehouse,
         'Low Stock' if p.is_low_stock else 'In Stock']
        for p in products
    ]
    return export_pdf('Products Report', headers, rows, 'products_report.pdf')


@login_required
def export_profit_loss_excel(request):
    from .export_utils import export_excel
    date_from, date_to = _get_date_range(request)
    sales_qs = Sale.objects.filter(sale_date__range=[date_from, date_to])
    monthly = sales_qs.extra(
        select={'month': "DATE_FORMAT(sale_date, '%%Y-%%m')"}
    ).values('month').annotate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('product__price'), output_field=DecimalField()))
    ).order_by('month')
    headers = ['Month', 'Revenue', 'Estimated Cost (60%)', 'Gross Profit', 'Margin %']
    rows = []
    for m in monthly:
        rev = float(m['revenue'] or 0)
        cost = rev * 0.6
        profit = rev - cost
        rows.append([m['month'], round(rev, 2), round(cost, 2), round(profit, 2),
                     f"{round((profit/rev*100) if rev else 0, 1)}%"])
    return export_excel(headers, rows, 'Profit & Loss', 'profit_loss.xlsx')


# ─── Data Engineering: ETL ────────────────────────────────────────────────────

@login_required
def etl_dashboard(request):
    logs = ETLLog.objects.order_by('-started_at')[:20]
    summaries = DailySalesSummary.objects.order_by('-date')[:30]
    return render(request, 'engineering/etl_dashboard.html', {'logs': logs, 'summaries': summaries})


@login_required
def run_etl(request):
    from .etl_pipeline import run_all_pipelines
    try:
        run_all_pipelines()
        messages.success(request, 'All ETL pipelines ran successfully.')
    except Exception as e:
        messages.error(request, f'ETL failed: {e}')
    return redirect('etl_dashboard')


@login_required
def data_import_view(request):
    if request.method == 'POST':
        from .data_import import import_products_from_file, import_sales_from_file
        file = request.FILES.get('file')
        import_type = request.POST.get('import_type')
        if not file:
            messages.error(request, 'Please select a file.')
            return redirect('data_import')
        if import_type == 'products':
            count, error = import_products_from_file(file)
        else:
            count, error = import_sales_from_file(file)
        if error:
            messages.error(request, f'Import failed: {error}')
        else:
            messages.success(request, f'Successfully imported {count} records.')
        return redirect('data_import')
    return render(request, 'engineering/data_import.html')


# ─── Data Mining ──────────────────────────────────────────────────────────────

@login_required
def clustering_view(request):
    clusters = ProductCluster.objects.select_related('product').order_by('cluster_id')
    cluster_groups = {}
    for c in clusters:
        label = c.cluster_label or f'Cluster {c.cluster_id}'
        cluster_groups.setdefault(label, []).append(c)
    return render(request, 'mining/clustering.html', {'cluster_groups': cluster_groups})


@login_required
def association_rules_view(request):
    rules = AssociationRule.objects.order_by('-lift')
    return render(request, 'mining/association_rules.html', {'rules': rules})


@login_required
def anomaly_view(request):
    anomalies = AnomalyRecord.objects.select_related('product').filter(is_anomaly=True).order_by('-sale_date')
    all_records = AnomalyRecord.objects.select_related('product').order_by('-sale_date')[:50]
    return render(request, 'mining/anomaly.html', {'anomalies': anomalies, 'all_records': all_records})


@login_required
def run_mining(request):
    from .etl_pipeline import run_clustering_etl, run_association_rules_etl, run_anomaly_detection_etl
    try:
        run_clustering_etl()
        run_association_rules_etl()
        run_anomaly_detection_etl()
        messages.success(request, 'Data mining completed successfully.')
    except Exception as e:
        messages.error(request, f'Mining failed: {e}')
    return redirect('clustering')
