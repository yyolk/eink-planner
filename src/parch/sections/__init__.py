"""section registry — name to class for compose. Coordinator fills the manifest; chase is still MOS."""

from parch.sections.cover_plain import CoverPlain
from parch.sections.index import Index
from parch.sections.annual import Annual
from parch.sections.quarterly import Quarterly
from parch.sections.monthly import Monthly
from parch.sections.weekly import Weekly
from parch.sections.daily import Daily
from parch.sections.daily_notes import DailyNotes
from parch.sections.projects import Projects
from parch.sections.meetings import Meetings
from parch.sections.habits import Habits
from parch.sections.review import Review
from parch.sections.tasks import Tasks
from parch.sections.colophon import Colophon

SECTIONS: dict[str, type] = {
    "cover_plain": CoverPlain,
    "index": Index,
    "annual": Annual,
    "quarterly": Quarterly,
    "monthly": Monthly,
    "weekly": Weekly,
    "daily": Daily,
    "daily_notes": DailyNotes,
    "projects": Projects,
    "meetings": Meetings,
    "habits": Habits,
    "review": Review,
    "tasks": Tasks,
    "colophon": Colophon,
}

__all__ = ["Colophon", "SECTIONS"]
