from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from accounts.views import login_view, logout_view
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.collection, name='collection'),
    path('shop/<slug:slug>/', views.collection, name='collection_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/drawer/', views.cart_drawer_data, name='cart_drawer_data'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),



    path('search/', views.search_view, name='search'),

    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    path('about/', views.about, name='about'),
    path('aboutus', RedirectView.as_view(pattern_name='store:about', permanent=False), name='aboutus_redirect'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),

    path('register/', RedirectView.as_view(pattern_name='accounts:signup', permanent=False), name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('account/', views.account, name='account'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
]