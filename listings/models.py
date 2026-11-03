from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """
    A product category shown as a large icon on the home page, e.g.
    Vehicles, Houses, Houses for rent, Land, Electronics, Others.
    """

    name = models.CharField(_("Izina"), max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    icon = models.ImageField(
        _("Ifoto"),
        upload_to="categories/",
        blank=True,
        null=True,
        help_text=_("Ifoto igaragara ku ishusho y'ubwoko ku rupapuro rw'ibanze."),
    )
    order = models.PositiveIntegerField(
        default=0, help_text=_("Umubare muto ugaragara mbere.")
    )

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("listings:category_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.name


class Listing(models.Model):
    """A single product a seller has posted for sale."""

    class Condition(models.TextChoices):
        NEW = "new", _("Gishya")
        USED = "used", _("Gikoreshejwe")

    class Currency(models.TextChoices):
        # RWF listed first so it's the default choice everywhere this
        # is used as a select field.
        RWF = "RWF", "RWF"
        USD = "USD", "$"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="listings", verbose_name=_("Ubwoko")
    )
    name = models.CharField(_("Izina"), max_length=150)
    description = models.TextField(_("Ibisobanuro"))
    condition = models.CharField(
        _("Uko bimeze"), max_length=10, choices=Condition.choices, default=Condition.USED
    )
    # Rwanda's administrative divisions, matching "District and sector"
    # from the spec.
    district = models.CharField(_("Akarere"), max_length=100)
    sector = models.CharField(_("Umurenge"), max_length=100)
    price = models.DecimalField(_("Igiciro"), max_digits=12, decimal_places=2)
    currency = models.CharField(
        _("Ifaranga"), max_length=3, choices=Currency.choices, default=Currency.RWF
    )
    is_active = models.BooleanField(
        default=True, help_text="Uncheck to hide this listing without deleting it."
    )
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        return reverse("listings:listing_detail", kwargs={"pk": self.pk})

    @property
    def location(self):
        return f"{self.sector}, {self.district}"

    @property
    def display_price(self):
        """Formatted as '$120.00' for USD or '5,000 RWF' for RWF,
        matching how each currency is normally written."""
        if self.currency == self.Currency.USD:
            return f"${self.price:,.2f}"
        return f"{self.price:,.0f} RWF"

    @property
    def cover_image(self):
        # Iterating self.images.all() in Python (rather than calling
        # .filter()/.first() on the manager) lets this reuse a
        # prefetch_related("images") cache when the caller has one,
        # instead of firing a fresh query per listing.
        images = list(self.images.all())
        for image in images:
            if image.is_cover:
                return image
        return images[0] if images else None

    def __str__(self):
        return self.name


class ListingImage(models.Model):
    """One photo attached to a listing. A listing can have several."""

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="listings/")
    is_cover = models.BooleanField(
        default=False, help_text="Shown first in the listings grid."
    )

    def __str__(self):
        return f"Photo for {self.listing.name}"


class Favorite(models.Model):
    """A buyer marking a listing as saved/favourited so they can find
    it again later from their own account."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="one_favorite_per_listing"),
        ]

    def __str__(self):
        return f"{self.user} \u2665 {self.listing}"
