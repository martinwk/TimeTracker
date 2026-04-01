"""
Aggregatielogica voor ActivityBlock en UniqueActivity.

Structuur na aggregatie:
    ActivityBlock
        └── UniqueActivity  (via unique_activities, één per unieke raw_title)
                └── occurrences → WindowActivity  (FK, één activiteit per UniqueActivity)

Algoritme per dag per app:
  1. Haal alle niet-ruis WindowActivity-regels op, gesorteerd op started_at
  2. Groepeer per app_name
  3. Loop door de activiteiten: open een nieuw blok als started_at >= deadline
  4. Binnen elk blok: groepeer op raw_title, tel seconden op
  5. Sla ActivityBlock op, daarna UniqueActivity per unieke titel
  6. Wijs elke WindowActivity via FK toe aan zijn UniqueActivity (bulk update)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

logger = logging.getLogger(__name__)

DEFAULT_BLOCK_MINUTES = 15


@dataclass
class AggregateResult:
    date: date
    blocks_created: int
    blocks_deleted: int
    activities_processed: int


@dataclass
class _TitleGroup:
    """Interne staat voor één unieke titel binnen een blok."""
    raw_title: str
    total_seconds: int = 0
    activity_ids: list = field(default_factory=list)

    def add(self, activity):
        self.total_seconds += activity.duration_seconds
        self.activity_ids.append(activity.pk)


@dataclass
class _OpenBlock:
    """Interne staat van een blok dat nog wordt opgebouwd."""
    app_name: str
    started_at: object
    ended_at: object
    block_minutes: int
    title_groups: dict = field(default_factory=dict)   # raw_title → _TitleGroup
    total_seconds: int = 0
    activity_count: int = 0

    @property
    def deadline(self):
        return self.started_at + timedelta(minutes=self.block_minutes)

    @property
    def dominant_title(self):
        """De titel met de meeste cumulatieve seconden in dit blok."""
        if not self.title_groups:
            return None
        return max(self.title_groups.values(), key=lambda g: g.total_seconds).raw_title

    def add(self, activity):
        self.ended_at = activity.ended_at
        self.total_seconds += activity.duration_seconds
        self.activity_count += 1
        if activity.raw_title not in self.title_groups:
            self.title_groups[activity.raw_title] = _TitleGroup(raw_title=activity.raw_title)
        self.title_groups[activity.raw_title].add(activity)


def _build_blocks_for_day(activities, block_minutes: int) -> list[_OpenBlock]:
    """
    Bouw een lijst van _OpenBlock objecten op uit een gesorteerde
    lijst van WindowActivity-regels voor één dag en één app.
    """
    blocks = []
    current = None

    for activity in activities:
        if current is None or activity.started_at >= current.deadline:
            if current is not None:
                blocks.append(current)
            current = _OpenBlock(
                app_name=activity.app_name,
                started_at=activity.started_at,
                ended_at=activity.ended_at,
                block_minutes=block_minutes,
            )
        current.add(activity)

    if current is not None:
        blocks.append(current)

    return blocks


def aggregate_day(target_date: date, block_minutes: int = DEFAULT_BLOCK_MINUTES) -> AggregateResult:
    """
    Aggregeer alle niet-ruis WindowActivity-regels voor één dag.

    Per blok worden UniqueActivity-records aangemaakt (één per unieke
    raw_title). Elke WindowActivity krijgt via een FK-update een
    verwijzing naar zijn UniqueActivity.

    Bij heraggregatie worden de FK's eerst gereset naar NULL, daarna
    worden de bestaande ActivityBlocks verwijderd (cascade verwijdert
    UniqueActivity mee), en dan wordt alles opnieuw opgebouwd.
    """
    from activities.models import ActivityBlock, UniqueActivity, WindowActivity

    # Reset FK op WindowActivity voor deze dag zodat SET_NULL niet
    # achterblijft als wees na het verwijderen van de blokken
    WindowActivity.objects.filter(date=target_date).update(unique_activity=None)

    # Verwijder bestaande blokken (cascade verwijdert UniqueActivity mee)
    # Count ActivityBlocks before deletion
    blocks_to_delete = ActivityBlock.objects.filter(date=target_date).count()
    ActivityBlock.objects.filter(date=target_date).delete()
    deleted_count = blocks_to_delete

    activities = (
        WindowActivity.objects
        .filter(date=target_date, is_noise=False)
        .order_by("started_at")
    )

    if not activities.exists():
        return AggregateResult(
            date=target_date,
            blocks_created=0,
            blocks_deleted=deleted_count,
            activities_processed=0,
        )

    # Groepeer per app
    by_app = defaultdict(list)
    for activity in activities:
        by_app[activity.app_name].append(activity)

    blocks_created = 0
    activities_processed = 0

    for app_name, app_activities in by_app.items():
        open_blocks = _build_blocks_for_day(app_activities, block_minutes)

        for ob in open_blocks:
            block = ActivityBlock.objects.create(
                app_name=ob.app_name,
                date=target_date,
                started_at=ob.started_at,
                ended_at=ob.ended_at,
                total_seconds=ob.total_seconds,
                activity_count=ob.activity_count,
                block_minutes=block_minutes,
            )

            # Maak UniqueActivity per unieke titel (desc op seconden)
            for title_group in sorted(
                ob.title_groups.values(),
                key=lambda g: g.total_seconds,
                reverse=True,
            ):
                unique = UniqueActivity.objects.create(
                    block=block,
                    raw_title=title_group.raw_title,
                    total_seconds=title_group.total_seconds,
                )
                # Wijs de WindowActivity-regels toe via FK (één bulk update)
                WindowActivity.objects.filter(
                    pk__in=title_group.activity_ids
                ).update(unique_activity=unique)

            blocks_created += 1
            activities_processed += ob.activity_count

    logger.info(
        "%s: %d blokken aangemaakt uit %d activiteiten (venster: %d min)",
        target_date, blocks_created, activities_processed, block_minutes,
    )

    # Voer rules toe voor deze dag
    logger.info("%s: Activityrules toepassen...", target_date)
    from activities.rule_engine import apply_rules
    rules_result = apply_rules(date_from=target_date, date_to=target_date)
    logger.info(
        "%s: %d rule-mappings aangemaakt, %d handmatige overgeslagen",
        target_date,
        rules_result.mappings_created,
        rules_result.mappings_skipped_manual,
    )

    return AggregateResult(
        date=target_date,
        blocks_created=blocks_created,
        blocks_deleted=deleted_count,
        activities_processed=activities_processed,
    )


def aggregate_range(
    date_from: date,
    date_to: date,
    block_minutes: int = DEFAULT_BLOCK_MINUTES,
) -> list[AggregateResult]:
    """
    Aggregeer alle dagen tussen date_from en date_to (inclusief).
    """
    results = []
    current = date_from
    while current <= date_to:
        results.append(aggregate_day(current, block_minutes))
        current += timedelta(days=1)
    return results