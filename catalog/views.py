from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import audit
from stock.services import apply_movement

from .forms import CategoryForm, ProductForm
from .models import Category, Product


@login_required
def products(request):
    tab = request.GET.get('tab', 'products')
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    ctx = {'tab': tab, 'q': q, 'cat': cat, 'category_form': CategoryForm()}
    if tab == 'categories':
        cats = Category.objects.annotate(n=Count('products'))
        if q:
            cats = cats.filter(name__icontains=q)
        ctx['categories'] = cats
    else:
        items = Product.objects.filter(is_active=True).select_related('category')
        if q:
            items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
        if cat.isdigit():
            items = items.filter(category_id=int(cat))
        ctx['items'] = items[:300]
    ctx['all_categories'] = Category.objects.all()
    return render(request, 'catalog/list.html', ctx)


@login_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if not Category.objects.exists():
        messages.warning(request, 'Add a category first, then add products.')
        return redirect('/catalog/?tab=categories')
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            product = form.save()
            opening = form.cleaned_data.get('opening_stock') or 0
            if opening:
                apply_movement(product, opening, 'opening', request.user, note='Opening stock')
        audit(request.user, 'Product added', f'{product.code} {product.name}')
        messages.success(request, f'{product.name} added.')
        return redirect('catalog:products')
    return render(request, 'catalog/product_form.html', {'form': form, 'title': 'Add product'})


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        audit(request.user, 'Product edited', f'{product.code} {product.name}')
        messages.success(request, 'Product updated.')
        return redirect('catalog:products')
    return render(request, 'catalog/product_form.html', {
        'form': form, 'title': f'Edit {product.code}', 'product': product})


@login_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, f'{product.name} deleted.')
    except ProtectedError:
        # Already used in an order or stock history: hide it instead so records stay intact.
        product.is_active = False
        product.save(update_fields=['is_active'])
        messages.info(request, f'{product.name} is used in past records, so it was archived instead of deleted.')
    audit(request.user, 'Product removed', f'{product.code} {product.name}')
    return redirect('catalog:products')


@login_required
@require_POST
def category_add(request):
    form = CategoryForm(request.POST)
    if form.is_valid():
        cat = form.save()
        audit(request.user, 'Category added', cat.name)
        messages.success(request, f'Category {cat.name} added.')
    else:
        messages.error(request, 'Enter a unique category name.')
    return redirect('/catalog/?tab=categories')


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        audit(request.user, 'Category edited', category.name)
        messages.success(request, 'Category updated.')
        return redirect('/catalog/?tab=categories')
    return render(request, 'catalog/category_form.html', {'form': form, 'category': category})


@login_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.error(request, 'Move or delete the products in this category first.')
    else:
        category.delete()
        audit(request.user, 'Category deleted', category.name)
        messages.success(request, 'Category deleted.')
    return redirect('/catalog/?tab=categories')

