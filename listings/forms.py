from django import forms
from django.utils.translation import gettext_lazy as _

from listings.templatetags.category_extras import get_category_display_name

from .models import Listing


class ListingForm(forms.ModelForm):
    """The seller's 'add listing' form: category, name, details,
    condition, location (district/sector) and price. Photos are
    handled separately in the view since a listing can have several."""

    class Meta:
        model = Listing
        fields = [
            "category",
            "name",
            "description",
            "condition",
            "district",
            "sector",
            "price",
            "currency",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show each category's name in the currently active site
        # language, matching the rest of the UI.
        self.fields["category"].label_from_instance = get_category_display_name
        self.fields["price"].widget.attrs.update({"step": "0.01", "min": "0"})
        self.fields["currency"].widget.attrs.update({"class": "form-select"})
        for name, field in self.fields.items():
            if name != "currency":
                field.widget.attrs.setdefault("class", "form-control")


class ListingSearchForm(forms.Form):
    """
    The search box in the nav bar / above a category's listings grid --
    a simple, immediate text search over listing names and location.
    """

    q = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Shakisha ukurikije aho biherereye..."),
                "class": "form-control",
            }
        ),
    )
