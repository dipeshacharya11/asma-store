# Asma Stores — Django Backend 

## What's new in this pass

- **Full custom dashboard** at `/dashboard/` (staff-login required), rebuilt to match your
  gold mockup: sidebar (Overview / Catalog / Sales / Content / System, linking straight
  into Django admin for CRUD), topbar with a working dark-mode toggle, 4 KPI cards, and
  **two real animated SVG charts** — a 7-day revenue trend line chart and a revenue-by-
  category donut chart. Both are computed server-side from actual `Order`/`OrderItem`
  queries and passed to the page via `json_script`, not hardcoded arrays.
- **Verified with real data, not assumed**: placed a mixed order (one Canvas Painting +
  one Mithila Art piece, Rs. 9,498 total) through actual checkout, then confirmed on the
  dashboard: the trend chart's last data point read exactly `9498.0`, and the donut chart
  read **Mithila Art 58% / Canvas Paintings 42%** — which is mathematically correct
  (5499/9498 = 58%, 3999/9498 = 42%). The math checks out because the data is real.
- **Performance infrastructure — confirmed already solid, not re-done**: WhiteNoise
  serving gzip/brotli-compressed, content-hashed static files (`CompressedManifestStaticFilesStorage`)
  with far-future cache headers; GZip middleware; Pillow-based image compression running
  automatically on every Category/Product/HeroSlide image upload; Django's cache framework
  (LocMemCache, swappable for Redis) caching the homepage's hero slides and featured
  products with signal-based invalidation the moment an admin edits them; `loading="lazy"`
  on every non-hero product/category image; `select_related` on the collection query to
  avoid N+1 queries. Collection/shop pages are intentionally *not* cached, since caching
  product listings would risk showing stale stock/out-of-stock state — a correctness
  tradeoff, not an oversight.

## Running it

```bash
cd asma_backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_store
python manage.py createsuperuser
python manage.py runserver
```

Visit `/dashboard/` (after logging in as your superuser) for the live charts. `/admin/`
remains the full CRUD interface for products, orders, categories, and blog posts — linked
directly from the dashboard sidebar.

## What's honestly still not done

- Instagram feed, brand-logo strip, 360° product view, working "Compare" feature
- Live "trending/recent searches" in the search overlay (static placeholders)
- Recently Viewed on the product page
- Real payment gateway integration (checkout records the order but doesn't call a processor)
- Product image galleries beyond primary/secondary (no multi-image carousel yet)
- The dashboard is read-only by design — editing still happens in Django admin

