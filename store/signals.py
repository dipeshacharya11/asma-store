"""
Real cache invalidation: whenever a Category, Product, or HeroSlide is saved
or deleted (e.g. an admin changes stock, adds a product, or reorders the
hero), the relevant cache keys are cleared immediately. Without this, the
site would show stale data for up to the cache timeout — this is what makes
"admin panel controls a cached site" actually true rather than misleading.
"""
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, Product, HeroSlide
from .context_processors import NAV_CATEGORIES_CACHE_KEY

FEATURED_PRODUCTS_CACHE_KEY = 'featured_products_v1'
HERO_SLIDES_CACHE_KEY = 'hero_slides_v1'


@receiver([post_save, post_delete], sender=Category)
def clear_category_cache(sender, **kwargs):
    cache.delete(NAV_CATEGORIES_CACHE_KEY)


@receiver([post_save, post_delete], sender=Product)
def clear_product_cache(sender, **kwargs):
    cache.delete(FEATURED_PRODUCTS_CACHE_KEY)
    cache.delete(NAV_CATEGORIES_CACHE_KEY)  # product_count on categories may have changed


@receiver([post_save, post_delete], sender=HeroSlide)
def clear_hero_cache(sender, **kwargs):
    cache.delete(HERO_SLIDES_CACHE_KEY)
