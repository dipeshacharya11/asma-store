from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

# Products low at or below this quantity are flagged "low stock" in the
# storefront. This is a real model-level constant used by both the admin
# list view and the product queries — not a frontend-only simulation.
LOW_STOCK_THRESHOLD = 8


def compress_image(image_field, max_width=1600, quality=78):
    """
    Resizes an uploaded image down to max_width (preserving aspect ratio) and
    re-saves it as a quality-78 JPEG. This is real server-side compression —
    it runs once at upload time, so every subsequent page load serves the
    already-shrunk file instead of a multi-MB phone photo.
    """
    img = Image.open(image_field)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    return ContentFile(buffer.getvalue())


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True,
                               help_text="Uploaded photo — automatically compressed and resized on save.")
    hero_gradient = models.CharField(
        max_length=255, blank=True,
        help_text="CSS fallback background, used only if no image is uploaded."
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.image and not getattr(self, '_image_compressed', False):
            import os
            compressed = compress_image(self.image, max_width=1200)
            filename = os.path.basename(self.image.name)
            self._image_compressed = True
            self.image.save(filename, compressed, save=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:collection_by_category', args=[self.slug])

    @property
    def product_count(self):
        return self.products.filter(is_active=True, stock__gt=0).count()

    @property
    def image_display_url(self):
        return self.image.url if self.image else None


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    sku = models.CharField(max_length=40, unique=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # --- Real inventory tracking ---
    # This single field drives every "in stock / low stock / out of stock"
    # decision across the storefront: the collection query excludes
    # stock=0 items, the detail page shows the live count, and checkout
    # decrements it atomically when an order is placed.
    stock = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)

    image = models.ImageField(upload_to='products/', blank=True, null=True,
                               help_text="Primary photo — automatically compressed and resized on save.")
    image_secondary = models.ImageField(upload_to='products/', blank=True, null=True,
                                         help_text="Hover/secondary photo — automatically compressed.")
    image_gradient = models.CharField(max_length=255, blank=True, help_text="CSS fallback, used only if no image uploaded.")
    image_gradient_secondary = models.CharField(max_length=255, blank=True)

    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    rating_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        import os
        if not self.slug:
            self.slug = slugify(self.name)
        if self.image and not getattr(self, '_image_compressed', False):
            compressed = compress_image(self.image, max_width=1400)
            filename = os.path.basename(self.image.name)
            self._image_compressed = True
            self.image.save(filename, compressed, save=False)
        if self.image_secondary and not getattr(self, '_image_secondary_compressed', False):
            compressed2 = compress_image(self.image_secondary, max_width=1400)
            filename2 = os.path.basename(self.image_secondary.name)
            self._image_secondary_compressed = True
            self.image_secondary.save(filename2, compressed2, save=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:product_detail', args=[self.slug])

    @property
    def is_low_stock(self):
        return 0 < self.stock <= LOW_STOCK_THRESHOLD

    @property
    def is_out_of_stock(self):
        return self.stock <= 0

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((1 - (self.price / self.compare_at_price)) * 100)
        return 0

    @property
    def primary_image_url(self):
        return self.image.url if self.image else None

    @property
    def secondary_image_url(self):
        return self.image_secondary.url if self.image_secondary else None


class HeroSlide(models.Model):
    """Admin-manageable panel for the homepage accordion hero."""
    title = models.CharField(max_length=200)
    eyebrow = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    cta_text = models.CharField(max_length=60, default='Shop Now')
    cta_url = models.CharField(max_length=200, default='/shop/')
    image = models.ImageField(upload_to='hero/', blank=True, null=True,
                               help_text="Upload a real hero photo — automatically compressed and resized on save.")
    image_url = models.URLField(
        blank=True,
        help_text="Fallback: a direct image URL (e.g. Unsplash link), used only if no image is uploaded above."
    )
    vertical_label = models.CharField(max_length=60, blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.image and not getattr(self, '_image_compressed', False):
            import os
            compressed = compress_image(self.image, max_width=1800)
            filename = os.path.basename(self.image.name)
            self._image_compressed = True
            self.image.save(filename, compressed, save=False)
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        """Prefer the uploaded, compressed image; fall back to the URL field."""
        if self.image:
            return self.image.url
        return self.image_url


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, blank=True, default='Verified Buyer')
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    excerpt = models.CharField(max_length=280, blank=True)
    content = models.TextField()
    image_gradient = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=100, default='Asma Stores')
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:blog_detail', args=[self.slug])


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    percent_off = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} — {self.full_name}"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    @property
    def discount(self):
        if self.coupon:
            return round(self.subtotal * self.coupon.percent_off / 100, 2)
        return 0

    @property
    def total(self):
        return self.subtotal - self.discount + self.shipping_cost


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)  # snapshot in case product is later deleted
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"
# ==========================================================================
# SIGNATURE COLLECTION
# ==========================================================================

class SignatureCollection(models.Model):
    name = models.CharField(
        max_length=120,
        help_text="Example: Oud Collection, Luxury Perfumes"
    )

    subtitle = models.CharField(
        max_length=180,
        blank=True
    )

    description = models.TextField(blank=True)

    products = models.ManyToManyField(
        Product,
        related_name="signature_collections",
        blank=True
    )

    sort_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Signature Collection"
        verbose_name_plural = "Signature Collections"

    def __str__(self):
        return self.name