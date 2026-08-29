"""section registry — name to class for compose. Coordinator fills the manifest; chase is still MOS."""

from parch.mos.sections.cover_plain import CoverPlain
from parch.mos.sections.index import Index
from parch.mos.sections.annual import Annual
from parch.mos.sections.quarterly import Quarterly
from parch.mos.sections.monthly import Monthly
from parch.mos.sections.weekly import Weekly
from parch.mos.sections.daily import Daily
from parch.mos.sections.daily_notes import DailyNotes
from parch.mos.sections.projects import Projects
from parch.mos.sections.meetings import Meetings
from parch.mos.sections.habits import Habits
from parch.mos.sections.review import Review
from parch.mos.sections.tasks import Tasks
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
