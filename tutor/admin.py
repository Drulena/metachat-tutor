"""The research desk: stock Django admin over the session ledger (ticket #35).

ADR-0007 decision 9 keeps this admin stock and extensible the Django way -
custom ``FieldListFilter`` subclasses, registered actions, template overrides -
because the ledger is a research artefact, not a learner surface: no page that
answers a learner reads it, so nothing here is allowed to become one.

The write path is the chat: rows are born at the intake form and appended to on
every submission (decision 1), so the admin never mints a session. What it does
is inspect, filter, and clean up: a researcher sees everything read-only, and
the maintainer - a superuser - is the only account that deletes, and deletes
through a filter, never by an abandonment policy (decision 7).
"""

from __future__ import annotations

import datetime
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode

from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ORDER_VAR, SEARCH_VAR
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch
from django.db.models.functions import Length
from django.utils.html import format_html, format_html_join
from django.utils.timezone import localtime

from .models import Assessment, Group, SessionRecord

# What a cell prints where a row has nothing to say: a null group (the ledger
# keeps the row when a group is deleted) and an unanswered gate.
EMPTY_CELL = "—"

# The stamp shape a researcher reads a lifecycle pair in: date first, so the
# column sorts and scans the same way top to bottom, and the time to the minute.
STAMP_FORMAT = "%Y-%m-%d %H:%M"

# A UUID v7 is 36 canonical characters - unreadable in a list column, while the
# first 8 disambiguate a cohort's sessions at a glance and stay searchable.
SHORT_ID_LENGTH = 8


def stamp(value: Optional[datetime.datetime]) -> str:
    """One lifecycle stamp as the list shows it; a null one prints a dash.

    Aware stamps are rendered in the admin's current time zone, so the
    "Started" column and the date-range filters agree on the local day.
    """
    if value is None:
        return EMPTY_CELL
    return localtime(value).strftime(STAMP_FORMAT)


def score_line(scores: Any) -> str:
    """The numbers a gate answer scored, joined for a table cell."""
    if not scores:
        return EMPTY_CELL
    return "·".join(str(score) for score in scores)


def rated_lines_html(rated: Any):
    """The task lines an answer rated, printed as the **rating form** printed them.

    The lines live in the answer form and not in the transcript, so the
    assessment row is the one place the stimulus a learner saw survives
    (ticket #48). A bare answer - a gate that named no lines - prints a dash.
    """
    pairs = [
        (item.get("letter", ""), item.get("prompt", ""))
        for item in rated
        if isinstance(item, dict)
    ]
    if not pairs:
        return EMPTY_CELL
    return format_html_join(
        "<br>", "{} {}", ((letter, prompt) for letter, prompt in pairs)
    )


class FinishedFilter(admin.SimpleListFilter):
    """The lifecycle question the ticket opens with: finished, or abandoned.

    The answer is one column - a null ``finished_at`` is what abandoned means
    (ADR-0007 decision 4) - so the filter reads that stamp directly and invents
    no status field (decision 7 rejects a status enum for exactly this reason).
    """

    title = "Finished"
    parameter_name = "finished"

    FINISHED = "finished"
    ABANDONED = "abandoned"

    def lookups(self, request, model_admin):
        """The two lifecycle states a session ledger row can be in."""
        return [(self.FINISHED, "Finished"), (self.ABANDONED, "Abandoned")]

    def queryset(self, request, queryset):
        """Cut the list to the state asked for; no choice leaves it whole."""
        if self.value() == self.FINISHED:
            return queryset.filter(finished_at__isnull=False)
        if self.value() == self.ABANDONED:
            return queryset.filter(finished_at__isnull=True)
        return queryset


class DateRangeFilter(admin.FieldListFilter):
    """A from/to window over one timestamp field, typed into the sidebar.

    Django's stock date filter answers named buckets (today, past 7 days) and
    Django 5.0 ships no range control, so the window is the documented custom
    ``FieldListFilter`` subclass. Its parameters are the field's own ``__date``
    extracts: a window is a run of local calendar days with both ends inside it,
    and the URL says which field it cuts and how far it reaches.
    """

    template = "tutor/admin/date_range_filter.html"
    #: The sidebar heading. ``FieldListFilter.__init__`` writes the field's
    #: verbose name over ``title``, so a subclass names itself below that.
    filter_title: Optional[str] = None

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        if self.filter_title is not None:
            self.title = self.filter_title
        # The changelist hands a multi-valued query dict over, so a popped
        # parameter arrives as the list of everything typed into that box;
        # the last value is the one the page shows (the stock filters' rule).
        self.used_parameters = {
            key: value[-1] if isinstance(value, (list, tuple)) else value
            for key, value in self.used_parameters.items()
        }
        self.since_param, self.until_param = self.expected_parameters()
        self.since_value = self.used_parameters.get(self.since_param) or ""
        self.until_value = self.used_parameters.get(self.until_param) or ""
        self.hidden_fields: list[tuple[str, str]] = []
        self.clear_link = "?"

    def expected_parameters(self) -> list[str]:
        """The two ends of the window, named by the field they cut."""
        return [f"{self.field_path}__date__gte", f"{self.field_path}__date__lte"]

    def choices(self, changelist):
        """The clear link, and the query a window submit has to carry along.

        A window is one control among several on this page, so the form keeps
        the other cuts standing. The changelist's own links drop the search box
        and the sort (they are not filter parameters), so this adds them back:
        the researcher narrows the list they are looking at.
        """
        kept = [
            (key, value)
            for key, value in parse_qsl(
                changelist.get_query_string(remove=self.expected_parameters()).lstrip(
                    "?"
                ),
                keep_blank_values=True,
            )
        ]
        for param in (SEARCH_VAR, ORDER_VAR):
            value = changelist.params.get(param)
            if value:
                kept.append((param, value))
        self.hidden_fields = kept
        clear_link = f"?{urlencode(kept)}" if kept else "?"
        return [
            {
                "selected": not self.used_parameters,
                "query_string": clear_link,
                "display": "All",
            }
        ]

    def queryset(self, request, queryset):
        """Apply the window, ignoring an end the researcher left blank.

        An empty date input is a half-open window, not a bad value: the query
        is built from what is there, and only a value that cannot be read as a
        date costs the request - the changelist answers with its warning, the
        way it does for any unreadable parameter.
        """
        bounds = {
            key: value
            for key, value in self.used_parameters.items()
            if value not in (None, "")
        }
        if not bounds:
            return queryset
        try:
            return queryset.filter(**bounds)
        except (ValidationError, ValueError) as exc:
            raise IncorrectLookupParameters(exc) from exc


class StartedRangeFilter(DateRangeFilter):
    """Sessions that began inside a window: the ledger's ``created_at``."""

    filter_title = "Started"


class ActivityRangeFilter(DateRangeFilter):
    """Sessions last written to inside a window - the abandonment cleanup cut."""

    filter_title = "Last activity"


class FinishedRangeFilter(DateRangeFilter):
    """Sessions that reached the terminal screen inside a window.

    A row with no stamp answers to no window on this field: asking when
    sessions finished cannot list sessions that never did.
    """

    filter_title = "Finished"


class AssessmentInline(admin.StackedInline):
    """The gate answers, printed on the page of the session they belong to.

    The ADR puts the ``Assessment`` rows beside the dialogue (decision 9): a
    session reads as one artefact - what the learner saw, what they answered,
    what it scored. Every field prints read-only, because a gate answer is
    written at acceptance and nothing here rewrites it.
    """

    model = Assessment
    extra = 0
    can_delete = False
    fields = ("kind", "raw_answer", "scores_line", "rated_lines", "created_at")
    readonly_fields = ("kind", "raw_answer", "scores_line", "rated_lines", "created_at")

    @admin.display(description="Scores")
    def scores_line(self, obj: Assessment) -> str:
        """The numbers the gate parsed from the answer."""
        return score_line(obj.scores)

    @admin.display(description="Rated lines")
    def rated_lines(self, obj: Assessment):
        """The task lines the answer rated, as the rating form printed them."""
        return rated_lines_html(obj.rated)

    def has_add_permission(self, request, obj=None) -> bool:
        """The chat writes a gate answer at acceptance; the desk never does."""
        return False


@admin.register(SessionRecord)
class SessionRecordAdmin(admin.ModelAdmin):
    """The ledger changelist: every session, in progress or finished.

    Columns are the ADR's list (decision 9) - who, which group, which level,
    the lifecycle pair, the gate scores, the reflection's length - and the
    page is a reading surface, not a form: the row's facts are written by the
    chat, so the list never edits them.
    """

    list_display = (
        "short_id",
        "participant",
        "group_line",
        "level_line",
        "started",
        "last_activity",
        "finished",
        "assessment_line",
        "reflection_size",
    )
    # The group is a method column, so the join has to be stated: one query
    # for a page of rows, not one per group name.
    list_select_related = ("group",)
    # The two questions a researcher arrives with: which id (the string the
    # export filename, the info button and the Summary carry) and who took
    # part. Groups are the filter dimension, not a search (decision 9).
    search_fields = ("session_id", "user_name")
    # The cuts decision 9 asks for: cohort, level, the lifecycle pair read as
    # finished/abandoned, and a window on each of the three stamps.
    list_filter = (
        "group",
        "level",
        FinishedFilter,
        ("created_at", StartedRangeFilter),
        ("updated_at", ActivityRangeFilter),
        ("finished_at", FinishedRangeFilter),
    )
    # Counted filters are a Django 5.0 opt-in, and a window typed into a box
    # has no counts to show: the toggle stays off, so the sidebar asks one
    # question per block and the range filters never meet the facet machinery.
    show_facets = admin.ShowFacets.NEVER
    ordering = ["-created_at"]
    # The row's own page is a reading surface: the dialogue beside the gate
    # answers it scored. Everything the chat wrote prints read-only - the id,
    # the lifecycle pair, the log, the reflection - and what a maintainer may
    # repair by hand is the registration a learner typed: the name, the group
    # it landed in, the level picked at the intake, and a reset chain link.
    inlines = [AssessmentInline]
    fieldsets = (
        ("Session", {"fields": ("session_id", "started", "last_activity", "finished")}),
        ("Participant", {"fields": ("user_name", "group", "level", "previous_session")}),
        ("Dialogue", {"fields": ("dialogue",)}),
        ("Reflection", {"fields": ("reflection",)}),
    )
    readonly_fields = (
        "session_id",
        "started",
        "last_activity",
        "finished",
        "dialogue",
        "reflection",
    )

    @admin.display(description="Session", ordering="session_id")
    def short_id(self, obj: SessionRecord) -> str:
        """The head of the canonical id: the row's own detail carries all 36."""
        return obj.session_id[:SHORT_ID_LENGTH]

    @admin.display(description="Participant", ordering="user_name")
    def participant(self, obj: SessionRecord) -> str:
        """The name the intake form registered."""
        return obj.user_name

    @admin.display(description="Group", ordering="group__name")
    def group_line(self, obj: SessionRecord) -> str:
        """The group as the intake spelled it; a deleted group is a dash."""
        return obj.group.name if obj.group_id is not None else EMPTY_CELL

    @admin.display(description="Level", ordering="level")
    def level_line(self, obj: SessionRecord) -> str:
        """The level axis as the model's choice spells it."""
        return obj.get_level_display()

    @admin.display(description="Started", ordering="created_at")
    def started(self, obj: SessionRecord) -> str:
        """The row's birth: the intake form's submission (decision 4)."""
        return stamp(obj.created_at)

    @admin.display(description="Last activity", ordering="updated_at")
    def last_activity(self, obj: SessionRecord) -> str:
        """The last write-through: the answer of an abandoned session dies here."""
        return stamp(obj.updated_at)

    @admin.display(description="Finished", ordering="finished_at")
    def finished(self, obj: SessionRecord) -> str:
        """The terminal stamp; a dash is what makes a session abandoned."""
        return stamp(obj.finished_at)

    @admin.display(description="Assessments")
    def assessment_line(self, obj: SessionRecord) -> str:
        """Every gate answer as ``kind scores``, oldest first.

        Reads the prefetch cache ``get_queryset`` builds, so a page of rows
        costs no extra query per session.
        """
        answers = list(obj.assessments.all())
        if not answers:
            return EMPTY_CELL
        return " ".join(f"{a.kind} {score_line(a.scores)}" for a in answers)

    @admin.display(description="Reflection", ordering="reflection_length")
    def reflection_size(self, obj: SessionRecord) -> int:
        """The reflection's length in characters, from the queryset annotation.

        A count, not the text: a page of reflections is a research read, not a
        table cell. The sort is the annotated length, so ordering this column
        orders the real values.
        """
        return obj.reflection_length

    def get_queryset(self, request):
        """Rows prepared for the page: group joined, gates prefetched, length counted.

        The annotation is what makes the Reflection column sortable, and the
        prefetch is what keeps the assessment summary off a per-row query.
        """
        return (
            super()
            .get_queryset(request)
            .annotate(reflection_length=Length("reflection"))
            .prefetch_related(
                Prefetch(
                    "assessments",
                    queryset=Assessment.objects.order_by("created_at", "id"),
                )
            )
        )

    def save_model(self, request, obj, form, change) -> None:
        """Write the repair, and leave the last-activity stamp where the chat put it.

        ``updated_at`` is the session's last activity (ADR-0007 decision 4) and
        the cut the abandonment cleanup filters by (decision 7), and the model's
        ``auto_now`` refreshes it on any save. A maintainer fixing a name a
        learner typed is not learner activity: the write puts back the stamp the
        row already carried, so an edited row cannot leave the window the
        cleanup is run from and disappear from research.
        """
        stamped = (
            self.model.objects.filter(pk=obj.pk)
            .values_list("updated_at", flat=True)
            .first()
            if change
            else None
        )
        super().save_model(request, obj, form, change)
        if stamped is not None:
            self.model.objects.filter(pk=obj.pk).update(updated_at=stamped)
            obj.updated_at = stamped

    @admin.display(description="Dialogue")
    def dialogue(self, obj: SessionRecord):

        """The dialogue log as the ledger kept it: every entry, in submit order.

        The learner's words and the model's answer are research data on this
        page, so they print escaped - the row is read, never executed. An entry
        the routing dropped, and an answer the model failed to give, carry the
        row's own flags, and the line says so: the reader sees why an entry
        answers nothing.
        """
        lines = [
            (entry.get("content", ""), _entry_line(entry))
            for entry in obj.chat_history
            if isinstance(entry, dict)
        ]
        if not lines:
            return EMPTY_CELL
        return format_html(
            "<dl>{}</dl>",
            format_html_join("", "<dt>{}</dt><dd>{}</dd>", ((line, content) for content, line in lines)),
        )

    def has_add_permission(self, request) -> bool:
        """The intake form is the ledger's writer; the desk inspects and cleans up.

        A row minted here would have no session behind it: no chat, no id from
        the mint, no intake facts. The ADR's one writer is the intake form
        (decision 1), so the admin page that would fabricate one is closed.
        """
        return False


def _entry_line(entry: dict) -> str:
    """The head line of one dialogue entry: who spoke, in which state, when.

    The row's own flags ride on the end - ``rejected`` for an input the routing
    dropped, ``llm_failed`` for an answer the model never gave - because a
    reader of the ledger needs to know why an entry answers nothing.
    """
    parts = [
        str(entry.get(key, ""))
        for key in ("role", "state", "timestamp")
        if entry.get(key)
    ]
    parts += [flag for flag in ("rejected", "llm_failed") if entry.get(flag)]
    return " · ".join(parts) or EMPTY_CELL


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """The cohort dimension: which groups the ledger knows, and how big each is.

    Read-only in every direction, and the reason is the group's own identity
    rule. A group is one row because of its casefolded key, and the intake form
    is the writer that keeps name and key in step (decision 5); renaming the
    display name here leaves the key behind, and the next learner who types the
    new spelling mints a second group of the same name. Deleting one is closed
    for a plainer reason: the ledger keeps the sessions and their group goes to
    null, which erases the dimension the research is cut by.
    """

    list_display = ("name", "session_count")
    search_fields = ("name",)
    ordering = ("name",)
    fields = ("name", "lookup_key")
    readonly_fields = ("name", "lookup_key")

    @admin.display(description="Sessions")
    def session_count(self, obj: Group) -> int:
        """How many ledger rows name this group - from the queryset annotation."""
        return obj.session_total

    def get_queryset(self, request):
        """Groups with their session count counted in the same query."""
        return super().get_queryset(request).annotate(session_total=Count("sessions"))

    def has_add_permission(self, request) -> bool:
        """The intake form creates a group on a miss; the desk does not."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """The intake form spells a group; a hand-edit splits its identity."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Deleting a group nulls the group of every session that named it."""
        return False


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """The gate answers across the corpus: one row per accepted answer.

    The session's own page is where a session's answers belong; this list is
    the same rows cut the other way - by kind, across cohorts - for the
    question "how did the pretests score". Written at acceptance, printed here
    as written.
    """

    list_display = ("session_line", "kind", "raw_answer", "scores_line", "created_at")
    list_filter = ("kind", ("session__group", admin.RelatedOnlyFieldListFilter))
    search_fields = ("session__session_id", "session__user_name")
    ordering = ("-created_at",)
    list_select_related = ("session", "session__group")
    fields = ("session", "kind", "raw_answer", "scores_line", "rated_lines", "created_at")
    readonly_fields = (
        "session",
        "kind",
        "raw_answer",
        "scores_line",
        "rated_lines",
        "created_at",
    )

    @admin.display(description="Session", ordering="session__session_id")
    def session_line(self, obj: Assessment) -> str:
        """The session this answer belongs to, named by the id that identifies it."""
        return f"{obj.session.session_id[:SHORT_ID_LENGTH]} {obj.session.user_name}"

    @admin.display(description="Scores")
    def scores_line(self, obj: Assessment) -> str:
        """The numbers the gate parsed from the answer."""
        return score_line(obj.scores)

    @admin.display(description="Rated lines")
    def rated_lines(self, obj: Assessment):
        """The task lines the answer rated, as the rating form printed them."""
        return rated_lines_html(obj.rated)

    def has_add_permission(self, request) -> bool:
        """A gate answer is written when the learner's answer is accepted."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """The answer a learner gave is theirs: the desk reads it, never edits it."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """The desk's delete mandate names abandoned sessions, not gate answers.

        The session's own page already refuses to delete an answer from beside
        the row (the inline's ``can_delete`` is off), so the list cannot offer
        what the row closes - and a corpus missing its scores is not a cleanup.
        """
        return False
