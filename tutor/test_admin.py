"""The research admin over the session ledger (ticket #35).

ADR-0007 decision 9: stock Django admin, kept extensible the Django way. The
seam is the admin's own HTTP surface - what a researcher or a maintainer types
and sees - plus the app config that keeps the view-only researcher group
stated. Tests ask for the admin URLs with the test client and read the painted
answer back; Django's own admin machinery is not under test here.

The rows are built through the ORM: the ledger is the model's own data, and
timestamps are pinned with a query-set ``update`` because ``created_at`` and
``updated_at`` are automatic stamps on the write path.
"""

from __future__ import annotations

import datetime
import re

from django.contrib.auth.models import Group as AuthGroup, Permission, User
from django.core.management import call_command
from django.test import TestCase

from .admin import EMPTY_CELL
from .apps import RESEARCHER_GROUP
from .ids import uuid7
from .models import Assessment, Group, SessionRecord

# The changelist a researcher opens first: every session ledger row.
SESSIONS = "/admin/tutor/sessionrecord/"

# Pinned on purpose as UTC midday: the range filters cut by local calendar day,
# and a timestamp far from local midnight stays the same day in any zone the
# runner's clock reports.
DAY_1 = datetime.datetime(2026, 1, 12, 12, 0, tzinfo=datetime.timezone.utc)
DAY_2 = datetime.datetime(2026, 1, 19, 12, 0, tzinfo=datetime.timezone.utc)
DAY_3 = datetime.datetime(2026, 1, 26, 12, 0, tzinfo=datetime.timezone.utc)


def make_session(
    *,
    user_name: str,
    group: str | None = None,
    level: str = "beginner",
    started: datetime.datetime = DAY_1,
    activity: datetime.datetime = DAY_1,
    finished: datetime.datetime | None = None,
    reflection: str = "",
    chat_history: list[dict] | None = None,
) -> SessionRecord:
    """One ledger row whose timestamps are pinned to the day asked for.

    ``finished`` stays null by default, because a null stamp is what makes a
    session abandoned (ADR-0007 decision 4).
    """
    row = SessionRecord.objects.create(
        session_id=uuid7(),
        user_name=user_name,
        level=level,
        group=None if group is None else Group.objects.get_or_create_casefolded(group)[0],
        reflection=reflection,
        chat_history=[] if chat_history is None else chat_history,
    )
    if finished is not None:
        SessionRecord.objects.filter(pk=row.pk).update(finished_at=finished)
    SessionRecord.objects.filter(pk=row.pk).update(created_at=started, updated_at=activity)
    row.refresh_from_db()
    return row


def staff_user(*, name: str, superuser: bool = False) -> User:
    """A staff account: the maintainer is a superuser, a researcher is in the group.

    The researcher's power comes from the group the app ships, so a researcher
    account is created with none of its own - the role is the group's, not the
    account's.
    """
    return User.objects.create_user(
        name, password="tutor-admin", is_staff=True, is_superuser=superuser
    )


class PageChecks:
    """Markup checks that name the rule when they fail.

    An admin page is tens of kilobytes of stock markup, and the default
    ``assertNotIn``/``assertNotContains`` failure dumps all of it into the run
    output - the report buries the one line that matters. Every check here
    carries the reason the page has to answer as it does.
    """

    def assert_shows(self, html: str, needle: str, why: str) -> None:
        """Assert the painted page shows ``needle``, and say what it proves."""
        self.assertIn(needle, html, f"{why}: the page does not show {needle!r}")

    def assert_hides(self, html: str, needle: str, why: str) -> None:
        """Assert the painted page does not carry ``needle``, and say why not."""
        self.assertNotIn(needle, html, f"{why}: the page carries {needle!r}")


class LedgerListTests(TestCase):
    """The changelist: every session, in progress or finished, is inspectable."""

    def setUp(self) -> None:
        self.maintainer = staff_user(name="maintainer", superuser=True)
        self.client.force_login(self.maintainer)

    def test_the_admin_answers_a_visitor_with_the_login_page(self):
        """Nothing of the ledger is served before a login."""
        self.client.logout()
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/admin/login/?next=/admin/")

    def test_an_signed_in_non_staff_user_cannot_open_the_admin(self):
        """Staff status is the gate: a learner's account is not a researcher's."""
        User.objects.create_user("learner", password="tutor-admin")
        self.client.force_login(User.objects.get(username="learner"))
        response = self.client.get("/admin/tutor/sessionrecord/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/admin/login/?next=/admin/tutor/sessionrecord/")

    def test_the_list_shows_every_session_including_the_abandoned_ones(self):
        """In-progress sessions are on the list: the row is born at the intake."""
        abandoned = make_session(user_name="Stacy", group="Blue Tigers")
        finished = make_session(
            user_name="Ben", group="Red Tigers", started=DAY_2, finished=DAY_2
        )
        response = self.client.get("/admin/tutor/sessionrecord/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stacy")
        self.assertContains(response, "Ben")
        self.assertEqual(
            {row.pk for row in response.context["cl"].queryset},
            {abandoned.pk, finished.pk},
        )

    def test_the_list_opens_with_the_newest_start_first(self):
        """``created_at`` is the start stamp, and it is the default sort."""
        make_session(user_name="Oldest", started=DAY_1, activity=DAY_1)
        make_session(user_name="Newest", started=DAY_3, activity=DAY_3)
        response = self.client.get("/admin/tutor/sessionrecord/")
        self.assertEqual(
            [row.user_name for row in response.context["cl"].queryset],
            ["Newest", "Oldest"],
        )

    def test_the_columns_print_the_research_facts_of_a_session(self):
        """One row reads as the ledger: who, which group, which level, the
        lifecycle pair, the gate scores and the reflection's length.

        The ADR lists these columns (decision 9); the bare model would show
        only ``SessionRecord(id, level, date)``, which hides the participant,
        the group and the whole lifecycle pair.
        """
        row = make_session(
            user_name="Stacy",
            group="Blue Tigers",
            level="intermediate",
            started=DAY_1,
            activity=DAY_2,
            finished=DAY_3,
            reflection="x" * 37,
        )
        Assessment.objects.create(
            session=row, kind="pretest", raw_answer="3 4 5", scores=[3, 4, 5]
        )
        Assessment.objects.create(
            session=row, kind="posttest", raw_answer="5 5 4", scores=[5, 5, 4]
        )
        response = self.client.get("/admin/tutor/sessionrecord/")
        self.assertContains(response, "Stacy")
        self.assertContains(response, "Blue Tigers")
        self.assertContains(response, "Intermediate")
        self.assertContains(response, "2026-01-12")
        self.assertContains(response, "2026-01-19")
        self.assertContains(response, "2026-01-26")
        self.assertContains(response, "37")
        self.assertContains(response, "pretest 3·4·5")
        self.assertContains(response, "posttest 5·5·4")
        # The id column is the short head of the id: the full 36 characters
        # belong to the detail page, the search box and the export filename.
        cells = re.findall(
            r'<(?:th|td) class="field-[^"]*"[^>]*>(.*?)</(?:th|td)>',
            response.content.decode(),
            re.S,
        )
        self.assertTrue(cells, "the changelist printed no data cells")
        self.assertTrue(
            any(row.session_id[:8] in cell for cell in cells),
            "the short session id is not in any column",
        )
        self.assertFalse(
            any(row.session_id in cell for cell in cells),
            "a column prints the whole 36-character id",
        )

    def test_a_session_without_a_group_or_gates_still_prints_its_row(self):
        """A group the ledger lost, and a session with no gates answered, are
        both real states of a row: the cells say so, they do not crash."""
        row = make_session(user_name="Stacy", group=None, level="advanced")
        response = self.client.get("/admin/tutor/sessionrecord/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stacy")
        self.assertContains(response, row.session_id[:8])
        self.assertContains(response, EMPTY_CELL)


class SortingTests(PageChecks, TestCase):
    """Every printed column is a sortable header (the ADR: "I need sorting")."""

    def setUp(self) -> None:
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        by_participant = {
            "Amelie": ("Blue Tigers", "advanced", DAY_3, 5),
            "Bella": ("Red Tigers", "beginner", DAY_1, 120),
            "Stacy": ("Blue Tigers", "intermediate", DAY_2, 37),
        }
        for name, (group, level, started, reflection) in by_participant.items():
            make_session(
                user_name=name,
                group=group,
                level=level,
                started=started,
                activity=started,
                reflection="x" * reflection,
            )

    def order_by(self, column: str, *, descending: bool = False) -> list[str]:
        """Ask the changelist to sort by a column, and name the rows back."""
        index = self.client.get(SESSIONS).context["cl"].list_display.index(column)
        response = self.client.get(
            SESSIONS, {"o": f"-{index}" if descending else str(index)}
        )
        return [row.user_name for row in response.context["cl"].queryset]

    def test_sorting_the_participant_column_puts_the_names_in_order(self):
        """A header click orders the list by what the column prints."""
        self.assertEqual(self.order_by("participant"), ["Amelie", "Bella", "Stacy"])
        self.assertEqual(
            self.order_by("participant", descending=True),
            ["Stacy", "Bella", "Amelie"],
        )

    def test_sorting_the_group_column_keeps_one_group_together(self):
        """The group column sorts by the group's name, ties broken by start."""
        self.assertEqual(self.order_by("group_line"), ["Amelie", "Stacy", "Bella"])

    def test_sorting_the_started_column_reads_the_lifecycle_pair(self):
        """The start stamp sorts oldest first, newest first on the second click."""
        self.assertEqual(self.order_by("started"), ["Bella", "Stacy", "Amelie"])
        self.assertEqual(
            self.order_by("started", descending=True), ["Amelie", "Stacy", "Bella"]
        )

    def test_sorting_the_finished_column_keeps_the_abandoned_rows_together(self):
        """A null stamp sorts as one value: the abandoned rows cluster."""
        SessionRecord.objects.filter(user_name="Stacy").update(finished_at=DAY_3)
        SessionRecord.objects.filter(user_name="Amelie").update(finished_at=DAY_1)
        self.assertEqual(self.order_by("finished"), ["Bella", "Amelie", "Stacy"])

    def test_sorting_the_reflection_column_orders_by_the_length_it_prints(self):
        """The count column sorts by the count, not by the printed digits."""
        self.assertEqual(self.order_by("reflection_size"), ["Amelie", "Stacy", "Bella"])

    def test_a_column_with_nothing_to_sort_stays_a_plain_header(self):
        """The gate summary is derived from child rows, so it prints no link."""
        header = re.search(
            r'<th[^>]*class="[^"]*column-assessment_line[^"]*"[^>]*>(.*?)</th>',
            self.client.get(SESSIONS).content.decode(),
            re.S,
        )
        self.assertIsNotNone(header, "the assessment column header is missing")
        self.assert_hides(
            header.group(1), "<a", "a derived column has nothing to sort by"
        )


class SearchTests(TestCase):
    """The search box answers the two questions a researcher arrives with."""

    def setUp(self) -> None:
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        self.stacy = make_session(user_name="Stacy", group="Blue Tigers")
        self.bella = make_session(user_name="Bella", group="Beta crew")

    def search(self, phrase: str) -> list[str]:
        """The participants a search phrase leaves on the list."""
        response = self.client.get(SESSIONS, {"q": phrase})
        self.assertEqual(response.status_code, 200)
        return [row.user_name for row in response.context["cl"].queryset]

    def test_searching_a_participant_name_finds_their_sessions(self):
        """Who took part: a name fragment is enough."""
        self.assertEqual(self.search("Sta"), ["Stacy"])

    def test_searching_the_canonical_session_id_finds_the_row(self):
        """The id the export filename carries is the id the box accepts."""
        self.assertEqual(self.search(self.bella.session_id), ["Bella"])

    def test_a_group_name_is_a_filter_not_a_search(self):
        """Groups are the filter dimension; the box is id and participant only."""
        self.assertEqual(self.search("Blue Tigers"), [])


class FilterTests(PageChecks, TestCase):
    """The sidebar answers the research cuts: group, level, lifecycle, dates.

    Three sessions, one per lifecycle shape and one per cohort, all on pinned
    local days: Stacy began Jan 12 and never finished, Bella began Jan 19 and
    finished Jan 26, Amelie began Jan 26 and never finished.
    """

    def setUp(self) -> None:
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        self.stacy = make_session(
            user_name="Stacy", group="Blue Tigers", level="beginner", started=DAY_1
        )
        self.bella = make_session(
            user_name="Bella",
            group="Red Tigers",
            level="advanced",
            started=DAY_2,
            activity=DAY_2,
            finished=DAY_3,
        )
        self.amelie = make_session(
            user_name="Amelie",
            group="Blue Tigers",
            level="intermediate",
            started=DAY_3,
            activity=DAY_3,
        )

    def names(self, **params) -> list[str]:
        """The participants left on the list when the sidebar params are applied."""
        response = self.client.get(SESSIONS, params)
        self.assertEqual(response.status_code, 200, params)
        return [row.user_name for row in response.context["cl"].queryset]

    def test_filtering_by_group_leaves_one_group_of_learners(self):
        """"By Group" is the filter the ticket asks for: one group at a time."""
        self.assertEqual(
            self.names(group__id__exact=str(self.bella.group_id)), ["Bella"]
        )
        self.assertEqual(
            self.names(group__id__exact=str(self.amelie.group_id)), ["Amelie", "Stacy"]
        )

    def test_filtering_by_level_leaves_one_level_of_the_axis(self):
        """The level axis is a filter beside the group."""
        self.assertEqual(self.names(level="beginner"), ["Stacy"])
        self.assertEqual(self.names(level="advanced"), ["Bella"])

    def test_the_finished_filter_leaves_only_sessions_that_reached_the_end(self):
        """"Only finished" is a filter choice, not a status column to scan."""
        self.assertEqual(self.names(finished="finished"), ["Bella"])

    def test_the_abandoned_filter_leaves_the_sessions_that_never_finished(self):
        """A null finish stamp is what abandoned means; the filter names it."""
        self.assertEqual(self.names(finished="abandoned"), ["Amelie", "Stacy"])

    def test_the_start_range_cuts_by_local_calendar_day(self):
        """Sessions starting in a window, both endpoints included."""
        self.assertEqual(
            self.names(
                created_at__date__gte="2026-01-19", created_at__date__lte="2026-01-26"
            ),
            ["Amelie", "Bella"],
        )
        self.assertEqual(
            self.names(created_at__date__gte="2026-01-13"), ["Amelie", "Bella"]
        )

    def test_a_start_range_that_ends_before_it_starts_answers_nothing(self):
        """A backwards window is a real answer, not a crash."""
        self.assertEqual(
            self.names(
                created_at__date__gte="2026-01-26", created_at__date__lte="2026-01-12"
            ),
            [],
        )

    def test_the_finish_range_leaves_out_the_sessions_with_no_stamp(self):
        """Asking when sessions finished cannot list sessions that never did."""
        self.assertEqual(self.names(finished_at__date__gte="2026-01-01"), ["Bella"])

    def test_the_last_activity_range_answers_the_cleanup_question(self):
        """Abandoned plus a last-activity window is how a maintainer cleans up."""
        self.assertEqual(self.names(updated_at__date__lte="2026-01-13"), ["Stacy"])
        self.assertEqual(
            self.names(finished="abandoned", updated_at__date__lte="2026-01-20"),
            ["Stacy"],
        )

    def test_the_filters_stack_into_one_research_cut(self):
        """A cohort, a lifecycle state and a window are one question at once."""
        self.assertEqual(
            self.names(
                group__id__exact=str(self.amelie.group_id),
                finished="abandoned",
                created_at__date__gte="2026-01-26",
            ),
            ["Amelie"],
        )

    def test_the_sidebar_prints_the_two_ends_of_every_date_window(self):
        """Start, last activity and finish are all answerable from the page."""
        response = self.client.get(SESSIONS)
        for field, heading in (
            ("created_at", "Started"),
            ("updated_at", "Last activity"),
            ("finished_at", "Finished"),
        ):
            self.assertContains(response, f'name="{field}__date__gte"', count=1)
            self.assertContains(response, f'name="{field}__date__lte"', count=1)
            self.assertContains(response, heading)

    def test_applying_a_date_window_keeps_the_cuts_already_chosen(self):
        """The window is one control among several: the rest of the query rides on."""
        html = self.client.get(
            SESSIONS,
            {
                "group__id__exact": str(self.amelie.group_id),
                "q": "Stacy",
                "o": "4",
            },
        ).content.decode()
        self.assertIn(f'name="group__id__exact" value="{self.amelie.group_id}"', html)
        self.assertIn('name="q" value="Stacy"', html)

    def test_an_unreadable_window_lands_back_on_the_unfiltered_list(self):
        """A date the box cannot read costs the window, not the page.

        The changelist's own contract for a parameter it cannot build a query
        from: drop the parameters, answer on the clean list (the ``e=1`` flag),
        and never a traceback.
        """
        response = self.client.get(SESSIONS, {"created_at__date__gte": "yesterday"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{SESSIONS}?e=1")
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row.user_name for row in response.context["cl"].queryset],
            ["Amelie", "Bella", "Stacy"],
        )

    def test_the_facets_toggle_never_reaches_the_date_windows(self):
        """Counted filters are off: a hand-typed toggle must not break the page."""
        response = self.client.get(SESSIONS, {"_facets": "1"})
        self.assertEqual(response.status_code, 200)
        self.assert_hides(
            response.content.decode(),
            "Hide counts",
            "counted filters are off, so the toggle cannot be on",
        )


class SessionDetailTests(PageChecks, TestCase):
    """The row's own page: the dialogue the ledger kept, and the gate answers.

    ADR-0007 decision 9 asks for a read-only detail that renders
    ``chat_history`` beside the ``Assessment`` rows, so the researcher reads a
    session the way the learner lived it - and the text a learner or a model
    wrote stays text.
    """

    def setUp(self) -> None:
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        self.row = make_session(
            user_name="Stacy",
            group="Blue Tigers",
            level="beginner",
            reflection="I softened my criticism.",
            chat_history=[
                {
                    "role": "assistant",
                    "content": "Rate the three messages 1-5.",
                    "state": "pretest",
                    "timestamp": "2026-01-12T12:00:00",
                },
                {
                    "role": "user",
                    "content": "3 4 5",
                    "state": "pretest",
                    "timestamp": "2026-01-12T12:01:00",
                },
                {
                    "role": "assistant",
                    "content": "<script>alert(1)</script> & \"quotes\" <b>bold</b>",
                    "state": "role_menu",
                    "timestamp": "2026-01-12T12:02:00",
                    "llm_failed": True,
                },
                {
                    "role": "user",
                    "content": "banana",
                    "state": "role_menu",
                    "timestamp": "2026-01-12T12:03:00",
                    "rejected": True,
                },
            ],
        )
        Assessment.objects.create(
            session=self.row,
            kind="pretest",
            raw_answer="3 4 5",
            scores=[3, 4, 5],
            rated=[
                {"letter": "A", "prompt": "*Softening criticism*"},
                {"letter": "B", "prompt": "*Aggressive formatting*"},
            ],
        )

    def detail(self) -> str:
        """The painted detail page for the row under test."""
        response = self.client.get(f"{SESSIONS}{self.row.pk}/change/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_the_detail_prints_the_dialogue_in_the_order_the_chat_wrote_it(self):
        """Every entry, verbatim, with the state it was produced under."""
        html = self.detail()
        for phrase in (
            "Rate the three messages 1-5.",
            "3 4 5",
            "banana",
            "pretest",
            "role_menu",
        ):
            self.assert_shows(html, phrase, "the dialogue log is not printed")
        self.assertLess(
            html.index("Rate the three messages"),
            html.index(">banana<"),
            "the dialogue prints out of submit order",
        )

    def test_the_detail_marks_the_entries_the_routing_dropped(self):
        """A rejected input and a failed answer are the row's own flags, printed."""
        html = self.detail()
        self.assert_shows(html, "rejected", "a dropped input says it was dropped")
        self.assert_shows(html, "llm_failed", "a failed answer says it failed")

    def test_the_detail_escapes_what_a_learner_and_the_model_wrote(self):
        """Research data is read, never executed: markup stays markup."""
        html = self.detail()
        self.assert_hides(html, "<script>alert(1)</script>", "page text is escaped")
        self.assert_shows(
            html, "&lt;script&gt;alert(1)&lt;/script&gt;", "the escape is visible"
        )
        self.assert_shows(html, "&lt;b&gt;bold&lt;/b&gt;", "markup in an answer is text")

    def test_the_detail_prints_the_gate_answers_beside_the_session(self):
        """The assessments are rows of their own, on the session's page."""
        html = self.detail()
        for phrase in ("pretest", "3 4 5", "3·4·5", "*Softening criticism*"):
            self.assert_shows(html, phrase, "the gate answers are not on the row")
        self.assert_shows(html, "*Aggressive formatting*", "every rated line prints")

    def test_the_lifecycle_pair_and_the_id_are_not_inputs(self):
        """The stamps and the id are the chat's writes: the page shows them.

        A field rendered read-only prints in a ``readonly`` block, not in a
        form control, so nothing on this page can move a fact the ledger wrote.
        """
        html = self.detail()
        for name in ("session_id", "created_at", "updated_at", "finished_at"):
            self.assert_hides(
                html, f'name="{name}"', f"{name} is the ledger's write, not a form field"
            )
        self.assert_shows(html, "2026-01-12 12:00", "the start stamp prints")

    def test_the_reflection_text_prints_and_is_not_a_form_field(self):
        """The reflection is the learner's answer: readable here, not editable."""
        html = self.detail()
        self.assert_shows(html, "I softened my criticism.", "the reflection prints")
        self.assert_hides(
            html, 'name="reflection"', "the learner's answer is not a field to edit"
        )

    def test_the_changelist_offers_no_way_to_write_a_session(self):
        """The intake form is the only writer; the desk inspects and cleans up."""
        html = self.client.get(SESSIONS).content.decode()
        self.assert_hides(
            html, f"{SESSIONS}add/", "a page of the ledger has no add offer"
        )
        self.assertEqual(
            self.client.get(f"{SESSIONS}add/").status_code,
            403,
            "the add view is open",
        )

    def test_the_detail_offers_no_way_to_write_a_gate_answer(self):
        """A gate answer is written at acceptance; the desk never adds one."""
        response = self.client.get("/admin/tutor/assessment/add/")
        self.assertEqual(response.status_code, 403)


class ResearcherRoleTests(PageChecks, TestCase):
    """The ADR's two seats at the desk: a researcher reads, a maintainer acts.

    The researcher group is the ADR's permission split (decision 9), shipped by
    the app so every environment gets the same desk. Its whole power is the
    three view permissions: the ledger is research data, and reading it is the
    job the role exists for.
    """

    def setUp(self) -> None:
        self.stacy = make_session(
            user_name="Stacy",
            group="Blue Tigers",
            chat_history=[
                {
                    "role": "user",
                    "content": "3 4 5",
                    "state": "pretest",
                    "timestamp": "2026-01-12T12:01:00",
                }
            ],
        )
        self.researcher = staff_user(name="researcher")
        AuthGroup.objects.get(name=RESEARCHER_GROUP).user_set.add(self.researcher)

    def researcher_get(self, path: str) -> int:
        """The answer a researcher gets from an admin page."""
        self.client.force_login(self.researcher)
        return self.client.get(path).status_code

    def test_the_desk_ships_a_view_only_researcher_group(self):
        """The group exists, and its power is exactly the three ledger views."""
        group = AuthGroup.objects.get(name=RESEARCHER_GROUP)
        self.assertEqual(
            {codename for codename, in group.permissions.values_list("codename")},
            {"view_sessionrecord", "view_group", "view_assessment"},
        )

    def test_a_migrate_run_leaves_the_same_view_only_group(self):
        """The group is the app's, ensured on every migrate: idempotent, and
        the views are re-stated, not accumulated."""
        group = AuthGroup.objects.get(name=RESEARCHER_GROUP)
        group.permissions.add(Permission.objects.get(codename="change_sessionrecord"))
        call_command("migrate", verbosity=0)
        group.refresh_from_db()
        self.assertEqual(
            {codename for codename, in group.permissions.values_list("codename")},
            {"view_sessionrecord", "view_group", "view_assessment"},
        )

    def test_a_researcher_opens_every_ledger_page(self):
        """The three models of the ledger are all on the desk."""
        self.client.force_login(self.researcher)
        for path in (
            "/admin/",
            SESSIONS,
            f"{SESSIONS}{self.stacy.pk}/change/",
            "/admin/tutor/group/",
            "/admin/tutor/assessment/",
        ):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_a_researcher_reads_the_session_and_cannot_edit_it(self):
        """View permission renders the row as text: the facts have no controls."""
        self.client.force_login(self.researcher)
        html = self.client.get(f"{SESSIONS}{self.stacy.pk}/change/").content.decode()
        self.assert_shows(html, "Stacy", "the researcher reads the participant")
        self.assert_shows(html, "3 4 5", "the researcher reads the dialogue")
        self.assert_hides(
            html, 'name="user_name"', "a view-only seat gets no field to edit"
        )
        self.assert_hides(html, 'name="_save"', "a view-only seat gets no save button")

    def test_a_researcher_who_posts_a_change_is_refused(self):
        """A POST is refused by the permission, not by a hidden form field."""
        self.client.force_login(self.researcher)
        response = self.client.post(
            f"{SESSIONS}{self.stacy.pk}/change/",
            {
                "user_name": "Someone else",
                "level": "advanced",
                "group": "",
                "previous_session": "",
                "assessments-TOTAL_FORMS": "0",
                "assessments-INITIAL_FORMS": "0",
                "assessments-MIN_NUM_FORMS": "0",
                "assessments-MAX_NUM_FORMS": "1000",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.stacy.refresh_from_db()
        self.assertEqual(self.stacy.user_name, "Stacy")

    def test_a_researcher_who_posts_a_delete_is_refused(self):
        """Cleanup is the maintainer's act: a researcher cannot remove a row."""
        self.client.force_login(self.researcher)
        response = self.client.post(f"{SESSIONS}{self.stacy.pk}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SessionRecord.objects.filter(pk=self.stacy.pk).exists())

    def test_a_researcher_sees_no_action_that_writes(self):
        """The action menu a researcher is offered has no delete in it."""
        self.client.force_login(self.researcher)
        html = self.client.get(SESSIONS).content.decode()
        self.assert_hides(
            html, 'value="delete_selected"', "a view-only seat is offered no delete"
        )
        self.assert_hides(html, 'name="_save"', "a view-only seat is offered no save")

    def test_the_maintainer_is_offered_the_delete_action(self):
        """The delete-selected action ships with the desk (decision 7)."""
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        self.assertContains(self.client.get(SESSIONS), 'value="delete_selected"')

    def test_the_maintainer_deletes_the_abandoned_rows_a_filter_selected(self):
        """The cleanup is filter-driven: choose the abandoned sessions, delete
        the selection through the standard confirmation, and the finished row
        is untouched. No abandonment policy is coded (decision 7)."""
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        abandoned = make_session(user_name="Walk-away", group="Blue Tigers")
        make_session(
            user_name="Graduate", group="Blue Tigers", started=DAY_2, finished=DAY_2
        )
        # The filter is the selection step: it is what puts the abandoned rows
        # in front of the maintainer, and what the delete is asked of.
        response = self.client.get(SESSIONS, {"finished": "abandoned"})
        self.assertEqual(
            {row.pk for row in response.context["cl"].queryset},
            {self.stacy.pk, abandoned.pk},
        )
        selected = [str(self.stacy.pk), str(abandoned.pk)]
        response = self.client.post(
            SESSIONS,
            {
                "action": "delete_selected",
                "index": "0",
                "select_across": "0",
                "_selected_action": selected,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure")
        self.client.post(
            SESSIONS,
            {
                "action": "delete_selected",
                "index": "0",
                "select_across": "0",
                "post": "yes",
                "_selected_action": selected,
            },
        )
        survivors = list(SessionRecord.objects.values_list("user_name", flat=True))
        self.assertEqual(survivors, ["Graduate"])

    def test_a_maintainer_repairs_a_registration_fact_and_no_fact_of_the_ledger(self):
        """What the desk may fix is what a learner typed; the stamps stay put."""
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        started, activity = self.stacy.created_at, self.stacy.updated_at
        response = self.client.post(
            f"{SESSIONS}{self.stacy.pk}/change/",
            {
                "user_name": "Stachya",
                "level": "intermediate",
                "group": "",
                "previous_session": "",
                "assessments-TOTAL_FORMS": "0",
                "assessments-INITIAL_FORMS": "0",
                "assessments-MIN_NUM_FORMS": "0",
                "assessments-MAX_NUM_FORMS": "1000",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.stacy.refresh_from_db()
        self.assertEqual(self.stacy.user_name, "Stachya")
        self.assertEqual(self.stacy.level, "intermediate")
        self.assertEqual(self.stacy.created_at, started)
        self.assertIsNone(self.stacy.finished_at)

    def test_a_repair_leaves_the_last_activity_stamp_where_the_chat_put_it(self):
        """An admin repair is not learner activity.

        ``updated_at`` is the session's last activity (ADR-0007 decision 4),
        and it is the cut the abandonment cleanup filters by (decision 7). A
        maintainer fixing a typed name must not move that stamp to today: the
        row would leave the "abandoned before this date" window and vanish from
        the very list the cleanup is run from.
        """
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        activity = self.stacy.updated_at
        self.client.post(
            f"{SESSIONS}{self.stacy.pk}/change/",
            {
                "user_name": "Stachya",
                "level": "beginner",
                "group": "",
                "previous_session": "",
                "assessments-TOTAL_FORMS": "0",
                "assessments-INITIAL_FORMS": "0",
                "assessments-MIN_NUM_FORMS": "0",
                "assessments-MAX_NUM_FORMS": "1000",
                "_save": "Save",
            },
        )
        self.stacy.refresh_from_db()
        self.assertEqual(self.stacy.user_name, "Stachya")
        self.assertEqual(self.stacy.updated_at, activity)
        self.assertEqual(
            [row.pk for row in self.client.get(
                SESSIONS, {"finished": "abandoned", "updated_at__date__lte": "2026-01-31"}
            ).context["cl"].queryset],
            [self.stacy.pk],
        )

    def test_a_group_name_cannot_be_renamed_from_the_desk(self):
        """A hand-rename would split one cohort into two rows.

        The group's identity is its casefolded key, and the intake form is the
        writer that keeps the pair in step (decision 5). Renaming the display
        name here leaves the key behind, so the next learner who types the new
        spelling mints a second group of the same name.
        """
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        group_id = self.stacy.group_id
        response = self.client.post(
            f"/admin/tutor/group/{group_id}/change/",
            {"name": "Red Tigers", "sessions-TOTAL_FORMS": "0", "sessions-INITIAL_FORMS": "0",
             "sessions-MIN_NUM_FORMS": "0", "sessions-MAX_NUM_FORMS": "0"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Group.objects.get(pk=group_id).name, "Blue Tigers")

    def test_the_group_detail_prints_its_name_as_text(self):
        """The desk reads groups; the intake form spells them."""
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        html = self.client.get(
            f"/admin/tutor/group/{self.stacy.group_id}/change/"
        ).content.decode()
        self.assert_shows(html, "Blue Tigers", "the group prints its own spelling")
        self.assert_hides(html, 'name="name"', "a group name is not a field to edit")

    def test_a_group_row_cannot_be_deleted_from_the_desk(self):
        """Deleting a group nulls it out of every session that named it."""
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        response = self.client.post(f"/admin/tutor/group/{self.stacy.group_id}/delete/", {"post": "yes"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Group.objects.filter(pk=self.stacy.group_id).exists())

    def test_a_gate_answer_cannot_be_deleted_from_the_desk(self):
        """A gate answer is the learner's record; cleanup is for abandoned sessions.

        The ADR's delete mandate names abandoned sessions (decision 7), and the
        inline already refuses to delete an answer - the list cannot offer what
        the row's own page closes.
        """
        answer = Assessment.objects.create(
            session=self.stacy, kind="pretest", raw_answer="3 4 5", scores=[3, 4, 5]
        )
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        self.assert_hides(
            self.client.get("/admin/tutor/assessment/").content.decode(),
            'value="delete_selected"',
            "the answer list offers no delete the row's own page closes",
        )
        response = self.client.post(
            f"/admin/tutor/assessment/{answer.pk}/delete/", {"post": "yes"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Assessment.objects.filter(pk=answer.pk).exists())

    def test_the_gate_answer_list_prints_its_rows_read_only(self):
        """The corpus view reads answers; it does not edit them."""
        Assessment.objects.create(
            session=self.stacy, kind="pretest", raw_answer="3 4 5", scores=[3, 4, 5]
        )
        self.client.force_login(staff_user(name="maintainer", superuser=True))
        html = self.client.get("/admin/tutor/assessment/").content.decode()
        self.assert_shows(html, "3 4 5", "the corpus view prints the answers")
        self.assert_hides(
            html,
            "/admin/tutor/assessment/add/",
            "a gate answer is written at acceptance, never typed here",
        )
        detail = self.client.get(
            f"/admin/tutor/assessment/{Assessment.objects.first().pk}/change/"
        ).content.decode()
        self.assert_shows(detail, "3 4 5", "the answer prints on its own page")
        self.assert_hides(
            detail, 'name="raw_answer"', "the answer a learner gave is not a field"
        )





