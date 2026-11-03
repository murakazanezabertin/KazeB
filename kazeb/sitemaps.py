from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from listings.models import Category, Listing


class ListingSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Listing.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ["core:home", "core:how_it_works", "core:terms", "core:privacy"]

    def location(self, item):
        return reverse(item)
