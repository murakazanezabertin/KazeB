from .models import Category


def categories(request):
    """
    Makes the category list available in every template without every
    view needing to query for it -- used for the "find by category"
    icon grid and the top navigation bar.
    """
    return {"nav_categories": Category.objects.all()}
