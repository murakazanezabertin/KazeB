from django import template
from django.templatetags.static import static
from django.utils.translation import get_language

register = template.Library()

# Maps a category slug to a bundled default photo, so categories look
# right the moment they're created -- an admin can still upload a
# different photo per category (Listings > Categories in /admin/),
# which always takes priority over this fallback.
DEFAULT_ICONS = {
    "vehicles": "images/categories/vehicles.jpg",
    "houses": "images/categories/houses.jpg",
    "houses-for-rent": "images/categories/houses-for-rent.jpg",
    "land": "images/categories/land.jpg",
    "electronics": "images/categories/electronics.jpg",
    "job-offers": "images/categories/job-offers.jpg",
    "home-materials": "images/categories/home-materials.jpg",
    "fashion": "images/categories/fashion.jpg",
    "musical-instruments": "images/categories/musical-instruments.jpg",
    "sports-materials": "images/categories/sports-materials.jpg",
    "agricultural": "images/categories/agricultural.jpg",
    "kids": "images/categories/kids.png",
    "others": "images/categories/others.png",
}

# Category *names* are data (rows in the database), not template
# source text, so Django's normal {% trans %} machinery doesn't touch
# them. This maps each bundled category's slug to its name in all
# three site languages so the label under each icon (and everywhere
# else a category name is shown) changes with the language switcher
# too. A category created later in /admin/ with a slug not listed here
# just falls back to whatever name was typed in for it there.
CATEGORY_NAMES = {
    "vehicles": {"rw": "Ibinyabiziga", "en": "Vehicles", "fr": "Véhicules"},
    "houses": {"rw": "Amazu", "en": "Houses", "fr": "Maisons"},
    "houses-for-rent": {"rw": "Amazu akodeshwa", "en": "Houses for rent", "fr": "Maisons à louer"},
    "land": {"rw": "Ubutaka", "en": "Land", "fr": "Terrains"},
    "electronics": {"rw": "Ibikoresho bya elegitoroniki", "en": "Electronics", "fr": "Électronique"},
    "job-offers": {"rw": "Imyanya y'akazi", "en": "Job offers", "fr": "Offres d'emploi"},
    "home-materials": {"rw": "Ibikoresho by'urugo", "en": "Home materials", "fr": "Matériel pour la maison"},
    "fashion": {"rw": "Imyambaro", "en": "Fashion", "fr": "Mode"},
    "musical-instruments": {"rw": "Ibikoresho by'umuziki", "en": "Musical instruments", "fr": "Instruments de musique"},
    "sports-materials": {"rw": "Ibikoresho bya siporo", "en": "Sports materials", "fr": "Équipement sportif"},
    "agricultural": {"rw": "Ubuhinzi n'ubworozi", "en": "Agricultural", "fr": "Agriculture"},
    "kids": {"rw": "Iby'abana", "en": "Kids", "fr": "Enfants"},
    "others": {"rw": "Ibindi", "en": "Others", "fr": "Autres"},
}


def get_category_display_name(category):
    """The category's name in the current site language, falling back
    to whatever is stored in the database for categories not in the
    bundled set above."""
    names = CATEGORY_NAMES.get(category.slug)
    if not names:
        return category.name
    lang = get_language() or "rw"
    lang = lang.split("-")[0]
    return names.get(lang, category.name)


@register.simple_tag
def category_default_icon(category):
    """Returns a static URL for a bundled icon matching the category's
    slug, or None if there isn't one (the template then falls back to
    a plain initial letter)."""
    path = DEFAULT_ICONS.get(category.slug)
    return static(path) if path else None


@register.simple_tag
def category_name(category):
    """Displays a category's name in whichever language is currently
    active."""
    return get_category_display_name(category)
