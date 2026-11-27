from .models import Category


# Paths that do not render the legacy Django navbar/category grid and
# therefore do not need the Category.objects.all() query. Skipping it
# here avoids one unnecessary database round-trip on every request to
# the React app shell and API endpoints.
_NO_CATEGORIES_PATHS = (
    "/api/",
    "/accounts/profile/",
    "/admin-dashboard/",
)


def categories(request):
    """
    Makes the category list available in every template without every
    view needing to query for it -- used for the "find by category"
    icon grid and the top navigation bar.
    """
    path = request.path_info
    if path == "/" or any(path.startswith(p) for p in _NO_CATEGORIES_PATHS):
        return {}
    return {"nav_categories": Category.objects.all()}
