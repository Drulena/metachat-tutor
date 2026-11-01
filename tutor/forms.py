"""Form field definitions for the intake form (ticket #37).

The registration facts are plain data, so the form is Django's: the
widget labels, the maxlength parity with the ledger columns, and the
rejection copy for an incomplete submit all come from here, and the
view stays three lines of plumbing.
"""

from django import forms

from .models import SessionRecord


class IntakeForm(forms.Form):
    """Name, group and self-assessed level - required, no defaults.

    A blank submit is refused with the field error shown above the
    fields (spec #33: the intake carries no default participant).
    """

    name = forms.CharField(
        max_length=50,
        label="Your name",
        help_text="Shown on every screen and in the export file name.",
        widget=forms.TextInput(
            attrs={"class": "intake-input", "autocomplete": "name", "autofocus": True}
        ),
    )
    group = forms.CharField(
        max_length=256,
        label="Group",
        help_text="Your class or cohort, exactly as your tutor writes it.",
        # The datalist in the template offers the groups already in the
        # ledger: the match is case-insensitive (#36), so a cohort that
        # types a new casing lands on the group it already has.
        widget=forms.TextInput(
            attrs={"class": "intake-input", "list": "known-groups", "autocomplete": "organization"}
        ),
    )
    level = forms.ChoiceField(
        choices=SessionRecord.LEVEL_CHOICES,
        label="Level",
        widget=forms.RadioSelect(attrs={"class": "intake-radio"}),
        help_text="Your own estimate; the pretest result is reported separately.",
    )
