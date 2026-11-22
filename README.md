# FoodMeal - Food Delivery Management System

A full-stack food delivery platform built with **Django 5.2, Django REST Framework, MySQL 8, Bootstrap 5 and Razorpay (test mode)**.
It has three roles - **Customer, Restaurant Owner, Admin** - a REST API, inventory management, order tracking,
email notifications and an automated test suite.

> UI inspiration: a purple "FoodMeal" dashboard (sidebar, category chips, dish cards, order summary).

## Features

| Role | What they can do |
|------|------------------|
| **Customer** | Register / login / reset password, browse restaurants, search & filter food (name, category, price, veg), cart, coupons, saved addresses, checkout with **Razorpay** or **Cash on Delivery**, live order tracking, order history + cancellation, reviews, profile |
| **Restaurant owner** | Create/edit restaurant profile (needs admin approval), add/edit/delete food with images, prices & availability, manage stock (low-stock alerts), accept/reject orders and update status, sales report with charts |
| **Admin** | Dashboard (customers, restaurants, food, orders, revenue, pending/completed orders, low stock) with Chart.js charts, manage customers & owners, approve/reject restaurants, manage orders, food, inventory, payments; categories and coupons via Django admin |

Highlights: custom email-login user model, role-based permissions (web + API), server-side price calculation,
transactional stock handling (`select_for_update`), duplicate-restock and duplicate-payment protection,
HMAC signature verification for Razorpay, email notifications, pagination, search/filter, responsive UI.

## Project structure

```
food_delivery/
├── manage.py  requirements.txt  .env.example  .gitignore  README.md
├── config/          settings, urls, api_urls, asgi, wsgi
├── core/            shared base model, permissions, decorators, validators, template filters, test factories
├── accounts/        User (email login + role), CustomerProfile, Address, auth views + API
├── restaurants/     Restaurant, Review, public pages, owner profile, API
├── food/            FoodCategory, FoodItem, menu/search pages, owner CRUD, API
├── cart/            Cart, CartItem, cart pages, coupon handling, API
├── orders/          Order, OrderItem, OrderStatusHistory, Coupon, checkout + workflow service, API
├── inventory/       Inventory model, stock reservation/restoration service, owner page, API
├── payments/        Payment model, Razorpay service, payment pages, API
├── notifications/   email service (registration, order, payment, status, contact)
├── dashboard/       home/about/contact, customer/owner/admin dashboards, seed_data command
├── templates/       base.html, dashboard_base.html, public/ customer/ restaurant/ admin/ emails/ partials/
├── static/          css/ js/ images/
└── media/           uploaded images (git-ignored)
```

## Quick start on Windows

Prerequisites: **Python 3.12+**, **MySQL 8** (running), Git.

```bat
cd food_delivery

:: 1. virtual environment
python -m venv venv
venv\Scripts\activate

:: 2. dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 3. configuration file
copy .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Paste the generated key into `.env` as `DJANGO_SECRET_KEY`, and set `DB_PASSWORD` (see step 4).

**4. Create the MySQL database** (MySQL command line or Workbench):

```sql
CREATE DATABASE food_delivery CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'food_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON food_delivery.* TO 'food_user'@'localhost';
GRANT ALL PRIVILEGES ON `test_food_delivery`.* TO 'food_user'@'localhost';
FLUSH PRIVILEGES;
```

(The last GRANT lets `manage.py test` create its temporary database.)

```bat
:: 5. migrations (this project ships WITHOUT migration files - generate them once, then commit them)
python manage.py makemigrations
python manage.py migrate

:: 6. demo data: categories, 3 restaurants, ~14 dishes with stock, coupons, demo users
python manage.py seed_data

:: 7. (optional) your own superuser - it automatically gets the "admin" role
python manage.py createsuperuser

:: 8. run
python manage.py runserver
```

Open **http://127.0.0.1:8000/**

> `makemigrations` must be run before the first `migrate` because the project uses a custom user model
> (`accounts.User`). Commit the generated `*/migrations/0001_initial.py` files to Git afterwards.

### Demo accounts (created by `seed_data`, password for all: `Demo@12345`)

| Role | Email |
|------|-------|
| Admin | admin@foodmeal.com |
| Restaurant owners | owner1@foodmeal.com (Burger Barn), owner2@foodmeal.com (Pizza Palace), owner3@foodmeal.com (Tokyo Bowl) |
| Customer | customer@foodmeal.com |

Coupons: `WELCOME20` (20% up to Rs.150, min order Rs.200) and `FLAT50` (Rs.50 off above Rs.300).
Change or delete these demo accounts before any real deployment.

## Configuration (.env)

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | **Required.** Long random string |
| `DJANGO_DEBUG` | `True` for development |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `DJANGO_SECURE_COOKIES` | `True` when served over HTTPS |
| `DB_ENGINE` | `mysql` (default) or `sqlite` (handy for quick tests) |
| `DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT` | MySQL connection |
| `RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET` | Razorpay **test** keys |
| `EMAIL_HOST / EMAIL_PORT / EMAIL_USE_TLS / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL` | SMTP |

### Razorpay (test mode)
1. Create a free account at razorpay.com, switch the dashboard to **Test Mode**, open *Account & Settings -> API Keys* and generate keys.
2. Put them in `.env` (`rzp_test_...`). The secret is only ever read on the server.
3. At checkout choose *Razorpay*, then pay with test card `4111 1111 1111 1111` (any future expiry, any CVV) or UPI `success@razorpay`.
4. The browser sends the three values Razorpay returns to `/payments/verify/`; the server recomputes the HMAC-SHA256 signature and only then marks the order paid.

### Email (SMTP)
Leave `EMAIL_HOST_USER` empty during development: emails are printed in the terminal running `runserver`.
For Gmail: enable 2-step verification, create an **App Password**, then set `EMAIL_HOST_USER` (your address) and `EMAIL_HOST_PASSWORD` (the app password).
Emails sent: registration, order confirmation, payment confirmation, order accepted, dispatched, delivered, cancelled, password reset, contact form.

## Order workflow

`Pending -> Confirmed -> Preparing -> Ready for Pickup -> Out for Delivery -> Delivered`, with `Cancelled` possible
from Pending/Confirmed. Customers may cancel Pending/Confirmed orders; owners (own restaurant) and admins can move
orders forward or reject them. Every change is stored in `OrderStatusHistory`.

* Stock is reserved (decreased) inside the same database transaction that creates the order.
* Cancelling restores the stock exactly once (`Order.stock_restored`).
* A paid online order that is cancelled gets payment status *Refund pending* (refund it from the Razorpay dashboard).
* COD orders become *paid* when delivered. "Revenue" everywhere means the total of **delivered** orders.

## REST API

Base URL `http://127.0.0.1:8000/api/`. Authenticate with `Authorization: Token <token>` (from `/api/login/`) or a logged-in session.
Lists are paginated (`?page=2`) and support `?search=` and `?ordering=`.

| Area | Endpoints |
|------|-----------|
| Auth | `POST /register/` `POST /login/` `POST /logout/` `POST /password-reset/` |
| Restaurants | `GET /restaurants/` `GET /restaurants/<id>/` `POST /restaurants/` `PUT/PATCH /restaurants/<id>/` `DELETE /restaurants/<id>/` (+ admin `POST /restaurants/<id>/approve/` and `/reject/`) |
| Food | `GET /foods/` (filters: `restaurant, category, is_veg, min_price, max_price, search`) `GET /foods/<id>/` `POST /foods/` `PUT/PATCH/DELETE /foods/<id>/` |
| Cart (customer) | `GET /cart/` `POST /cart/add/` `PUT /cart/update/` `DELETE /cart/remove/` |
| Orders | `POST /orders/` (from the cart) `GET /orders/` `GET /orders/<id>/` `PATCH /orders/<id>/status/` |
| Payments | `POST /payments/create/` `POST /payments/verify/` |
| Inventory | `GET /inventory/` `POST /inventory/` `GET/PUT/PATCH /inventory/<id>/` |

Example (PowerShell or Git Bash; use `curl.exe` on Windows PowerShell):

```bash
curl -X POST http://127.0.0.1:8000/api/login/ -H "Content-Type: application/json" \
     -d '{"email":"customer@foodmeal.com","password":"Demo@12345"}'

curl -X POST http://127.0.0.1:8000/api/cart/add/ -H "Authorization: Token <token>" \
     -H "Content-Type: application/json" -d '{"food_item": 1, "quantity": 2}'

curl -X POST http://127.0.0.1:8000/api/orders/ -H "Authorization: Token <token>" \
     -H "Content-Type: application/json" -d '{"address_id": 1, "payment_method": "cod"}'
```

Status codes: `200/201/204` success, `400` validation or business-rule error, `401/403` not logged in / not allowed, `404` not found.

## Tests

```bat
python manage.py test
```

The suite covers registration/login, role permissions, restaurant and food CRUD, cart rules, inventory (stock validation,
low stock, single restoration), order placement/cancellation/status workflow, Razorpay signature verification
(gateway calls are mocked), REST API responses, and a smoke test that renders every page for every role.

To run quickly without MySQL: `set DB_ENGINE=sqlite` (cmd) or `$env:DB_ENGINE="sqlite"` (PowerShell), then `python manage.py test`.
Run one app: `python manage.py test orders`.

## Security notes

Password hashing (PBKDF2), CSRF on every form and AJAX call, session cookies `HttpOnly`, role checks on every view and API
endpoint, ownership checks (`restaurant__owner=request.user`), ORM-only queries, template auto-escaping, image
validation (type via Pillow + 2 MB limit), secrets only in `.env`, all prices/totals computed server-side, Razorpay signature
verification with constant-time comparison, no account enumeration on password reset, safe `next` redirects.
Before going live: set `DJANGO_DEBUG=False`, `DJANGO_SECURE_COOKIES=True`, a real `ALLOWED_HOSTS`, serve media/static via
a web server, and replace the demo passwords.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install mysqlclient` fails | Upgrade pip (`python -m pip install -U pip`); use Python 3.12 64-bit. As a fallback install `pymysql` and add `import pymysql; pymysql.install_as_MySQLdb()` at the top of `manage.py` and `config/__init__.py`. |
| `ModuleNotFoundError: pkg_resources` | `pip install "setuptools<81"` (already in requirements.txt). |
| `Access denied for user` | Check `DB_USER` / `DB_PASSWORD` in `.env` and the GRANT statements above. |
| `ImproperlyConfigured: DJANGO_SECRET_KEY` | You forgot to copy `.env.example` to `.env`. |
| Test DB permission error | Run the extra `GRANT` for `test_food_delivery`, or use `DB_ENGINE=sqlite` for tests. |
| Payment page says "not configured" | Add Razorpay test keys to `.env` and restart the server. |
| Uploaded images not showing | Keep `DJANGO_DEBUG=True` in development (media is served only in debug mode). |

## Roadmap ideas
Live delivery map, WebSocket order updates, restaurant opening-hours enforcement, refunds through the Razorpay API,
Celery for background emails, Docker setup.
