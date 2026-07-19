import random
import time

import requests

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from store.models import Category, Product


PRODUCTS = [
    {
        "category": "Perfumes",
        "name": "Midnight Oud Eau de Parfum",
        "sku": "PERF-001",
        "description": "A deep luxurious oud fragrance with warm woody notes.",
        "price": 89.00,
        "compare_at_price": 110.00,
        "image": "https://images.unsplash.com/photo-1458538977777-0549b2370168?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Perfumes",
        "name": "Golden Essence Perfume",
        "sku": "PERF-002",
        "description": "Elegant fragrance with floral and warm amber notes.",
        "price": 75.00,
        "compare_at_price": 95.00,
        "image": "https://plus.unsplash.com/premium_photo-1676748933022-e1183e997436?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Perfumes",
        "name": "Royal Amber",
        "sku": "PERF-003",
        "description": "A sophisticated amber fragrance for everyday luxury.",
        "price": 68.00,
        "compare_at_price": 82.00,
        "image": "https://images.unsplash.com/photo-1541643600914-78b084683601?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Perfumes",
        "name": "Velvet Rose",
        "sku": "PERF-004",
        "description": "Soft rose petals blended with musk and warm vanilla.",
        "price": 72.00,
        "compare_at_price": 90.00,
        "image": "https://images.unsplash.com/photo-1594035910387-fea47794261f?q=80&w=1200&auto=format&fit=crop",
    },

    {
        "category": "Deodorants",
        "name": "Urban Fresh Deodorant",
        "sku": "DEO-001",
        "description": "Long-lasting freshness designed for active lifestyles.",
        "price": 18.00,
        "compare_at_price": 24.00,
        "image": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Deodorants",
        "name": "Ocean Mist Body Spray",
        "sku": "DEO-002",
        "description": "Clean aquatic freshness with a crisp modern finish.",
        "price": 21.00,
        "compare_at_price": 28.00,
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Deodorants",
        "name": "Classic Musk Spray",
        "sku": "DEO-003",
        "description": "Warm musk fragrance with dependable all-day freshness.",
        "price": 20.00,
        "compare_at_price": 26.00,
        "image": "https://images.unsplash.com/photo-1608248597279-f99d160bfcbc?q=80&w=1200&auto=format&fit=crop",
    },

    {
        "category": "Gift Sets",
        "name": "Luxury Fragrance Gift Box",
        "sku": "GIFT-001",
        "description": "A curated fragrance gift collection for special occasions.",
        "price": 125.00,
        "compare_at_price": 155.00,
        "image": "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Gift Sets",
        "name": "Golden Celebration Gift Set",
        "sku": "GIFT-002",
        "description": "An elegant premium gift set presented in luxury packaging.",
        "price": 145.00,
        "compare_at_price": 180.00,
        "image": "https://images.unsplash.com/photo-1513885535751-8b9238bd345a?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Gift Sets",
        "name": "Signature Gift Collection",
        "sku": "GIFT-003",
        "description": "A sophisticated collection created for memorable gifting.",
        "price": 110.00,
        "compare_at_price": 140.00,
        "image": "https://images.unsplash.com/photo-1602173574767-37ac01994b2a?q=80&w=1200&auto=format&fit=crop",
    },

    {
        "category": "Body Care",
        "name": "Silk Body Lotion",
        "sku": "BODY-001",
        "description": "Rich daily body lotion for soft and nourished skin.",
        "price": 32.00,
        "compare_at_price": 42.00,
        "image": "https://images.unsplash.com/photo-1556229010-6c3f2c9ca5f8?q=80&w=1200&auto=format&fit=crop",
    },
    {
        "category": "Body Care",
        "name": "Luxury Body Oil",
        "sku": "BODY-002",
        "description": "Lightweight nourishing body oil with a luxurious finish.",
        "price": 38.00,
        "compare_at_price": 48.00,
        "image": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?q=80&w=1200&auto=format&fit=crop",
    },
]


CATEGORY_GRADIENTS = {
    "Perfumes": "linear-gradient(145deg,#17120c,#b58b3c)",
    "Deodorants": "linear-gradient(145deg,#dce8e8,#607d7d)",
    "Gift Sets": "linear-gradient(145deg,#5b1f29,#d4af62)",
    "Body Care": "linear-gradient(145deg,#eadfd2,#b99473)",
}

# Real subcategories per top-level category — this is what customers
# actually browse by (e.g. "Perfumes" -> "Men's Perfume"). Products aren't
# auto-reassigned into these (that stays a deliberate admin action per
# product), but the navigable category structure now genuinely exists.
SUBCATEGORY_DATA = {
    "Perfumes": [
        ("Men's Perfume", "linear-gradient(145deg,#101820,#3a536b)"),
        ("Women's Perfume", "linear-gradient(145deg,#3a1620,#b06a80)"),
        ("Unisex Perfume", "linear-gradient(145deg,#20201a,#8a8060)"),
    ],
    "Deodorants": [
        ("Men's Deodorant", "linear-gradient(145deg,#1c2b2b,#4f6f6f)"),
        ("Women's Deodorant", "linear-gradient(145deg,#2b1c26,#805a70)"),
    ],
    "Gift Sets": [
        ("Gifts for Him", "linear-gradient(145deg,#2a1a10,#8a5a30)"),
        ("Gifts for Her", "linear-gradient(145deg,#3a1420,#a85a70)"),
        ("Couple Sets", "linear-gradient(145deg,#241a30,#6a4a8a)"),
    ],
    "Body Care": [
        ("Lotions & Creams", "linear-gradient(145deg,#e8ded0,#b09070)"),
        ("Bath & Shower", "linear-gradient(145deg,#dce8e4,#7fa898)"),
    ],
}


class Command(BaseCommand):
    help = "Seed Asma Stores with demo categories and products"

    def download_image(self, url):
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")

        if not content_type.startswith("image/"):
            raise ValueError(
                f"URL did not return an image: {content_type}"
            )

        return response.content

    def handle(self, *args, **options):

        self.stdout.write("Starting Asma Stores seeder...")

        categories = {}

        for index, name in enumerate(CATEGORY_GRADIENTS, start=1):

            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"Explore our premium {name.lower()} collection.",
                    "hero_gradient": CATEGORY_GRADIENTS[name],
                    "sort_order": index,
                    "is_active": True,
                },
            )

            categories[name] = category

            status = "Created" if created else "Exists"

            self.stdout.write(
                f"{status} category: {name}"
            )

        for parent_name, subs in SUBCATEGORY_DATA.items():
            parent = categories.get(parent_name)
            if not parent:
                continue
            for sub_index, (sub_name, sub_gradient) in enumerate(subs, start=1):
                sub_category, sub_created = Category.objects.get_or_create(
                    name=sub_name,
                    defaults={
                        "parent": parent,
                        "description": f"Shop {sub_name.lower()}.",
                        "hero_gradient": sub_gradient,
                        "sort_order": sub_index,
                        "is_active": True,
                    },
                )
                status = "Created" if sub_created else "Exists"
                self.stdout.write(f"  {status} subcategory: {parent_name} -> {sub_name}")

        for index, data in enumerate(PRODUCTS, start=1):

            product, created = Product.objects.get_or_create(
                sku=data["sku"],
                defaults={
                    "name": data["name"],
                    "category": categories[data["category"]],
                    "description": data["description"],
                    "price": data["price"],
                    "compare_at_price": data["compare_at_price"],
                    "stock": random.randint(10, 60),
                    "is_active": True,
                    "is_featured": index <= 6,
                    "is_new": index >= 7,
                    "rating": random.choice([
                        4.5,
                        4.6,
                        4.7,
                        4.8,
                        4.9,
                        5.0,
                    ]),
                    "rating_count": random.randint(15, 250),
                },
            )

            if not created:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping existing product: {product.name}"
                    )
                )
                continue

            try:
                self.stdout.write(
                    f"Downloading image for {product.name}..."
                )

                image_data = self.download_image(data["image"])

                filename = f"{data['sku'].lower()}.jpg"

                product.image.save(
                    filename,
                    ContentFile(image_data),
                    save=False,
                )

                product.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created: {product.name}"
                    )
                )

            except Exception as exc:

                self.stdout.write(
                    self.style.ERROR(
                        f"Image failed for {product.name}: {exc}"
                    )
                )

                product.save()

            time.sleep(0.4)

        self.stdout.write(
            self.style.SUCCESS(
                "\nAsma Stores demo products seeded successfully."
            )
        )