import json
import urllib.parse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify

from shop.form import CustomUserForm
from .models import Cart, Catagory, Favourite, Product


def home(request):
    products = Product.objects.filter(trending=1)
    return render(request, "shop/index.html", {"products": products})


# ================= FAVORITE =================

def favviewpage(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to view your favourites.")
        return redirect("/login/?next=/favviewpage/")

    fav = Favourite.objects.filter(user=request.user)
    return render(request, "shop/fav.html", {"fav": fav})


def remove_fav(request, fid):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to manage your favourites.")
        return redirect("/login/")

    item = Favourite.objects.filter(id=fid, user=request.user).first()
    if item:
        item.delete()
        messages.success(request, "Item removed from favourites.")
    else:
        messages.error(request, "Item not found in favourites.")

    return redirect("/favviewpage/")


def fav_page(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'Login to Add Favourite'}, status=200)

        try:
            data = json.load(request)
            product_id = data.get('pid')
            product = Product.objects.filter(id=product_id).first()

            if not product:
                return JsonResponse({'status': 'Product Not Found'}, status=404)

            if Favourite.objects.filter(user=request.user, product_id=product_id).exists():
                return JsonResponse({'status': 'Product Already in Favourite'}, status=200)

            Favourite.objects.create(user=request.user, product_id=product_id)
            return JsonResponse({'status': 'Product Added to Favourite'}, status=200)
        except Exception:
            return JsonResponse({'status': 'An error occurred'}, status=400)

    return JsonResponse({'status': 'Invalid Access'}, status=200)


# ================= CART =================

def cart_page(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to view your cart.")
        return redirect("/login/?next=/cart/")

    cart = Cart.objects.filter(user=request.user)
    return render(request, "shop/cart.html", {"cart": cart})


def remove_cart(request, cid):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to manage your cart.")
        return redirect("/login/")

    cartitem = Cart.objects.filter(id=cid, user=request.user).first()
    if cartitem:
        cartitem.delete()
        messages.success(request, "Item removed from cart.")
    else:
        messages.error(request, "Item not found in your cart.")

    return redirect("/cart/")


def add_to_cart(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'Login to Add Cart'}, status=200)

        try:
            data = json.load(request)
            product_qty = int(data.get('product_qty', 1))
            product_id = data.get('pid')
            product = Product.objects.filter(id=product_id).first()

            if not product:
                return JsonResponse({'status': 'Product Not Found'}, status=404)

            if Cart.objects.filter(user=request.user, product_id=product_id).exists():
                return JsonResponse({'status': 'Product Already in Cart'}, status=200)

            if product.quantity >= product_qty:
                Cart.objects.create(
                    user=request.user,
                    product_id=product_id,
                    product_qty=product_qty
                )
                return JsonResponse({'status': 'Product Added to Cart'}, status=200)
            else:
                return JsonResponse({'status': 'Product Stock Not Available'}, status=200)
        except Exception:
            return JsonResponse({'status': 'An error occurred'}, status=400)

    return JsonResponse({'status': 'Invalid Access'}, status=200)


def checkout(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to proceed to checkout.")
        return redirect("/login/?next=/cart/")

    cart_items = Cart.objects.filter(user=request.user)
    if not cart_items.exists():
        messages.warning(request, "Your cart is empty. Add products to checkout.")
        return redirect("/collections/")

    total = sum(item.total_cost for item in cart_items)
    cart_items.delete()
    messages.success(request, f"Order placed successfully! Total amount: Rs. {int(total)}. Thank you for shopping with ShopKart!")
    return redirect("/cart/")


# ================= AUTHENTICATION =================

def login_page(request):
    if request.user.is_authenticated:
        return redirect("/")

    next_url = request.POST.get('next', '').strip() or request.GET.get('next', '').strip()

    if request.method == 'POST':
        name = request.POST.get('username', '').strip()
        pwd = request.POST.get('password', '')

        if not name or not pwd:
            messages.error(request, "Please enter both username and password.")
            return render(request, "shop/login.html", {'username': name, 'next': next_url})

        # Flexible lookup: case-insensitive username or email
        user_obj = User.objects.filter(username__iexact=name).first()
        if not user_obj and '@' in name:
            user_obj = User.objects.filter(email__iexact=name).first()

        user = None
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=pwd)
            if not user and pwd.strip() != pwd:
                user = authenticate(request, username=user_obj.username, password=pwd.strip())
        else:
            user = authenticate(request, username=name, password=pwd)

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is inactive. Please contact support.")
                return render(request, "shop/login.html", {'username': name, 'next': next_url})

            login(request, user)
            # Store user metadata in signed session cookie for serverless resilience
            request.session['_auth_user_meta'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'password': user.password,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
            messages.success(request, f"Welcome back, {user.username}!")

            # Safe redirect: only redirect if next_url starts with '/' and not '//'
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect("/")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
            return render(request, "shop/login.html", {'username': name, 'next': next_url})

    return render(request, "shop/login.html", {'next': next_url})


def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "Logged out successfully.")
    return redirect("/")


def register(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately upon registration
            login(request, user)
            request.session['_auth_user_meta'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'password': user.password,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
            messages.success(
                request,
                f"Registration successful! Welcome to ShopKart, {user.username}!"
            )
            return redirect('/')
        else:
            messages.error(
                request,
                "Please correct the errors below and try again."
            )
    else:
        form = CustomUserForm()

    return render(request, "shop/register.html", {'form': form})


# ================= COLLECTIONS & PRODUCTS =================

def _find_category(raw_name):
    """Robust category lookup supporting URL-encoded, slugified, or numeric ID forms."""
    if not raw_name:
        return None
    raw = str(raw_name).strip()
    unquoted = urllib.parse.unquote(raw).strip()
    plus_unquoted = urllib.parse.unquote_plus(raw).strip()

    if raw.isdigit():
        cat = Catagory.objects.filter(id=int(raw)).first()
        if cat:
            return cat

    for cand in [unquoted, plus_unquoted, raw]:
        if cand:
            cat = Catagory.objects.filter(name__iexact=cand).first()
            if cat:
                return cat

    target_slugs = {slugify(unquoted), slugify(plus_unquoted), slugify(raw)}
    target_slugs.discard("")
    for cat in Catagory.objects.all():
        if slugify(cat.name) in target_slugs:
            return cat

    for cand in [unquoted, plus_unquoted, raw]:
        if cand and len(cand) >= 3:
            cat = Catagory.objects.filter(name__icontains=cand).first()
            if cat:
                return cat

    return None


def _find_product(raw_pname, raw_cname=None):
    """Robust product lookup supporting IDs, decoded names, slugs, and fuzzy matching."""
    if not raw_pname:
        return None
    raw_p = str(raw_pname).strip()
    unquoted_p = urllib.parse.unquote(raw_p).strip()
    plus_p = urllib.parse.unquote_plus(raw_p).strip()

    # 1. Check numeric ID
    if raw_p.isdigit():
        prod = Product.objects.filter(id=int(raw_p)).first()
        if prod:
            return prod
    if unquoted_p.isdigit():
        prod = Product.objects.filter(id=int(unquoted_p)).first()
        if prod:
            return prod

    # 2. Case-insensitive exact match
    for cand in [unquoted_p, plus_p, raw_p]:
        if cand:
            prod = Product.objects.filter(name__iexact=cand).first()
            if prod:
                return prod

    # 3. Slugified match
    target_slugs = {slugify(unquoted_p), slugify(plus_p), slugify(raw_p)}
    target_slugs.discard("")
    for p in Product.objects.all():
        if slugify(p.name) in target_slugs:
            return p

    # 4. Replace hyphens with spaces or spaces with hyphens
    for cand in [unquoted_p, plus_p, raw_p]:
        if '-' in cand:
            spaced = cand.replace('-', ' ')
            prod = Product.objects.filter(name__iexact=spaced).first()
            if prod:
                return prod
        if ' ' in cand:
            hyphened = cand.replace(' ', '-')
            prod = Product.objects.filter(name__iexact=hyphened).first()
            if prod:
                return prod

    # 5. Partial / contains match
    for cand in [unquoted_p, plus_p, raw_p]:
        if cand and len(cand) >= 3:
            prod = Product.objects.filter(name__icontains=cand).first()
            if prod:
                return prod

    # 6. Scoped category match if category name provided
    if raw_cname:
        category = _find_category(raw_cname)
        if category:
            for cand in [unquoted_p, plus_p, raw_p]:
                if cand:
                    prod = Product.objects.filter(category=category, name__icontains=cand).first()
                    if prod:
                        return prod

    return None


def collections(request):
    q = request.GET.get('q', '').strip()
    if q:
        prod = Product.objects.filter(
            Q(name__icontains=q) |
            Q(vendor__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q)
        ).distinct()
        return render(
            request,
            'shop/products/index.html',
            {
                'products': prod,
                'category_name': f'Search: "{q}"',
                'query': q,
            }
        )

    category = Catagory.objects.filter(status=0)
    return render(request, "shop/collections.html", {"catagory": category})


def collectionsview(request, name):
    category = _find_category(name)
    if category:
        products = Product.objects.filter(category=category)
        return render(
            request,
            "shop/products/index.html",
            {
                "products": products,
                "category_name": category.name,
            }
        )
    else:
        messages.warning(request, "No Such Category Found")
        return redirect('collections')


def product_details(request, cname, pname):
    product = _find_product(pname, cname)
    if product:
        return render(
            request,
            "shop/products/product_details.html",
            {"products": product}
        )

    # If product not found, check if category exists to provide clear feedback
    category = _find_category(cname)
    if not category and cname:
        messages.error(request, "No Such Category Found")
    else:
        messages.error(request, "No Such Product Found")
    return redirect('collections')


def product_details_by_id(request, pid):
    product = Product.objects.filter(id=pid).first()
    if product:
        return render(
            request,
            "shop/products/product_details.html",
            {"products": product}
        )
    messages.error(request, "No Such Product Found")
    return redirect('collections')


def product_details_by_name(request, pname):
    return product_details(request, cname="", pname=pname)
