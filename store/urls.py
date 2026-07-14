from django.urls import path
from django.contrib.auth import views as auth_views
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

    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),

    path('search/', views.search_view, name='search'),

    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='store/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='store:home'), name='logout'),
    path('account/', views.account, name='account'),
]
