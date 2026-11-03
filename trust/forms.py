from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PhoneVerification, Report, Review


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "reason": _("Impamvu"),
            "details": _("Ibisobanuro birambuye (si ngombwa)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect,
            "comment": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "rating": _("Amanota"),
            "comment": _("Icyo wavuga (si ngombwa)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comment"].widget.attrs.setdefault("class", "form-control")


class PhoneVerifyForm(forms.Form):
    code = forms.CharField(
        label=_("Kode wahawe"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "placeholder": "123456",
        }),
    )

    def __init__(self, *args, verification=None, **kwargs):
        self.verification = verification
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data["code"]
        verification = self.verification

        if verification.attempts >= PhoneVerification.MAX_ATTEMPTS:
            raise forms.ValidationError(
                _("Wagerageje inshuro nyinshi. Saba kode nshya.")
            )
        if verification.is_expired():
            raise forms.ValidationError(_("Kode yarangiye igihe. Saba indi."))
        if code != verification.code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            raise forms.ValidationError(_("Kode ntabwo ari yo."))
        return code
