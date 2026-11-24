import json
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render

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


# ================= COLLECTIONS =================

def collections(request):
    q = request.GET.get('q')
    if q:
        prod = Product.objects.filter(name__icontains=q)
        return render(request, 'shop/products/index.html', {'products': prod})

    category = Catagory.objects.filter(status=0)
    return render(request, "shop/collections.html", {"catagory": category})


def collectionsview(request, name):
    if Catagory.objects.filter(name=name, status=0).exists():
        products = Product.objects.filter(category__name=name)
        return render(
            request,
            "shop/products/index.html",
            {
                "products": products,
                "category_name": name
            }
        )
    else:
        messages.warning(request, "No Such Category Found")
        return redirect('collections')


def product_details(request, cname, pname):
    if Catagory.objects.filter(name=cname, status=0).exists():
        product = Product.objects.filter(name=pname, status=0).first()
        if product:
            return render(
                request,
                "shop/products/product_details.html",
                {"products": product}
            )
        else:
            messages.error(request, "No Such Product Found")
            return redirect('collections')
    else:
        messages.error(request, "No Such Category Found")
        return redirect('collections')
