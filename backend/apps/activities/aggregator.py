"""
Aggregatielogica voor ActivityBlock en UniqueActivity.

Algoritme: vaste 15-minutenraster per dag (96 slots).
Per slot worden alle WindowActivity-records die overlap hebben met
dat slot gecombineerd. Daardoor zijn overlappende ActivityBlocks
structureel onmogelijk.

Structuur na aggregatie:
    ActivityBlock (één per bezet 15-min-slot)
        └── UniqueActivity  (één per unieke raw_title binnen het slot)
                └── occurrences → WindowActivity  (FK)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)

DEFAULT_BLOCK_MINUTES = 15


@dataclass
class AggregateResult:
    date: date
    blocks_created: int
    blocks_deleted: int
    activities_processed: int


def aggregate_day(target_date: date, block_minutes: int = DEFAULT_BLOCK_MINUTES) -> AggregateResult:
    """
    Aggregeer alle niet-ruis WindowActivity-regels voor één dag
    via een vast raster van block_minutes-slots.

    Per slot worden alle activiteiten verzameld die overlap hebben
    met dat slot. dominant_title = titel met meeste overlap-seconden.
    total_seconds = som van overlap-seconden (max = block_minutes * 60).

    Bij heraggregatie worden bestaande blokken eerst verwijderd.
    """
    from apps.activities.models import ActivityBlock, UniqueActivity, WindowActivity, BlockProjectHistory

    # Snapshot handmatige toewijzingen vóór verwijdering (Optie C).
    # Sleutel: started_at (altijd exact hetzelfde 15-min raster).
    manual_snapshot = {
        entry["block__started_at"]: entry["project_id"]
        for entry in BlockProjectHistory.objects
            .filter(block__date=target_date, assigned_by="manual")
            .values("block__started_at", "project_id")
    }

    # Reset FK zodat SET_NULL geen wezen achterlaat na cascade-delete
    WindowActivity.objects.filter(date=target_date).update(unique_activity=None)

    blocks_to_delete = ActivityBlock.objects.filter(date=target_date).count()
    ActivityBlock.objects.filter(date=target_date).delete()
    deleted_count = blocks_to_delete

    activities = list(
        WindowActivity.objects
        .filter(date=target_date, is_noise=False)
        .order_by("started_at")
    )

    if not activities:
        return AggregateResult(
            date=target_date,
            blocks_created=0,
            blocks_deleted=deleted_count,
            activities_processed=0,
        )

    # Lokale middernacht als anker voor het raster
    local_midnight = make_aware(datetime.combine(target_date, time.min))
    slots_per_day  = (24 * 60) // block_minutes

    blocks_created       = 0
    activities_processed = set()   # pk's — één activiteit kan meerdere slots raken

    for slot_idx in range(slots_per_day):
        slot_start = local_midnight + timedelta(minutes=slot_idx * block_minutes)
        slot_end   = slot_start + timedelta(minutes=block_minutes)

        # Activiteiten met overlap: begint vóór slot_end én eindigt ná slot_start
        slot_acts = [
            a for a in activities
            if a.started_at < slot_end and a.ended_at > slot_start
        ]
        if not slot_acts:
            continue

        # Overlap-seconden per unieke raw_title
        title_secs: dict[str, int]        = defaultdict(int)
        title_ids:  dict[str, list[int]]  = defaultdict(list)

        for act in slot_acts:
            overlap = (
                min(act.ended_at, slot_end) - max(act.started_at, slot_start)
            ).total_seconds()
            title_secs[act.raw_title] += int(overlap)
            title_ids[act.raw_title].append(act.pk)
            activities_processed.add(act.pk)

        total_seconds  = min(sum(title_secs.values()), block_minutes * 60)
        dominant_title = max(title_secs, key=lambda t: title_secs[t])

        # Welke app_name? Gebruik de app van de dominante titel
        dominant_act = next(
            a for a in slot_acts if a.raw_title == dominant_title
        )

        block = ActivityBlock.objects.create(
            app_name      = dominant_act.app_name,
            date          = target_date,
            started_at    = slot_start,
            ended_at      = slot_end,
            total_seconds = total_seconds,
            activity_count= len(slot_acts),
            block_minutes = block_minutes,
        )

        # UniqueActivity per unieke titel (gesorteerd: meeste overlap eerst)
        for raw_title in sorted(title_secs, key=lambda t: title_secs[t], reverse=True):
            unique = UniqueActivity.objects.create(
                block         = block,
                raw_title     = raw_title,
                total_seconds = title_secs[raw_title],
            )
            WindowActivity.objects.filter(
                pk__in=title_ids[raw_title]
            ).update(unique_activity=unique)

        blocks_created += 1

    logger.info(
        "%s: %d blokken aangemaakt uit %d activiteiten (venster: %d min)",
        target_date, blocks_created, len(activities_processed), block_minutes,
    )

    # Herstel handmatige toewijzingen (Optie C).
    # Loopt vóór de rule engine zodat herstelde blokken worden overgeslagen.
    # project_id=None betekent: handmatig ontkoppeld — geen project herstellen,
    # maar wél een null-history aanmaken zodat de rule engine het blok overslaat.
    if manual_snapshot:
        from apps.projects.models import Project
        non_null_ids = {pid for pid in manual_snapshot.values() if pid is not None}
        project_cache = {
            p.pk: p for p in Project.objects.filter(pk__in=non_null_ids)
        }
        blocks_to_update = []
        history_records  = []
        for block in ActivityBlock.objects.filter(
            date=target_date, started_at__in=manual_snapshot.keys()
        ):
            project_id = manual_snapshot[block.started_at]
            if project_id is None:
                # Handmatig ontkoppeld: project leeg laten, history aanmaken om rule engine te blokkeren
                history_records.append(
                    BlockProjectHistory(block=block, project=None, assigned_by="manual")
                )
            else:
                project = project_cache.get(project_id)
                if project:
                    block.project = project
                    blocks_to_update.append(block)
                    history_records.append(
                        BlockProjectHistory(block=block, project=project, assigned_by="manual")
                    )
        if blocks_to_update:
            ActivityBlock.objects.bulk_update(blocks_to_update, ["project"])
        if history_records:
            BlockProjectHistory.objects.bulk_create(history_records)

    logger.info("%s: Activityrules toepassen...", target_date)
    from apps.activities.rule_engine import apply_rules
    rules_result = apply_rules(date_from=target_date, date_to=target_date)
    logger.info(
        "%s: %d blokken toegewezen via regels, %d handmatig ingesteld overgeslagen",
        target_date,
        rules_result.blocks_assigned,
        rules_result.blocks_skipped_manual,
    )

    return AggregateResult(
        date=target_date,
        blocks_created=blocks_created,
        blocks_deleted=deleted_count,
        activities_processed=len(activities_processed),
    )


def aggregate_range(
    date_from: date,
    date_to: date,
    block_minutes: int = DEFAULT_BLOCK_MINUTES,
) -> list[AggregateResult]:
    """Aggregeer alle dagen tussen date_from en date_to (inclusief)."""
    results = []
    current = date_from
    while current <= date_to:
        results.append(aggregate_day(current, block_minutes))
        current += timedelta(days=1)
    return results
