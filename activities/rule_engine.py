"""
Rule engine voor het automatisch koppelen van UniqueActivities aan projecten.

Algoritme:
  1. Haal alle actieve ActivityRules op, gesorteerd op prioriteit (laag = belangrijk)
  2. Voor elke UniqueActivity: loop through regels totdat één matcht
  3. Bij eerste match: verwijder oudere rule-gebaseerde mappings, maak nieuwe aan
  4. Handmatige mappings worden nooit overschreven (skipped)
  5. Return statistieken: aangemaakt, skipped, al handmatig
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from activities.models import ActivityRule, UniqueActivity
from projects.models import ActivityMapping, TimeEntry

logger = logging.getLogger(__name__)


@dataclass
class ApplyRulesResult:
    """Resultaat van apply_rules() operatie."""
    mappings_created: int
    mappings_skipped_manual: int  # Handmatige mappings niet overschreven
    unique_activities_processed: int


def apply_rules(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ApplyRulesResult:
    """
    Voer alle actieve ActivityRules toe op UniqueActivities.

    Args:
        date_from: Startdatum (inclusief). Geen filter als None.
        date_to: Einddatum (inclusief). Geen filter als None.

    Returns:
        ApplyRulesResult met tellingen

    Gedrag:
      - Rule-gebaseerde mappings voor verwerkte activities worden eerst verwijderd
      - Bij elke UniqueActivity: eerste matchende regel (op prioriteit) wordt gebruikt
      - Handmatige mappings worden nooit overschreven
      - Idempotent: meerdere keer draaien geeft dezelfde resultaat
    """
    # Haal active rules op, sorteren op prioriteit (laag eerst)
    rules = ActivityRule.objects.filter(is_active=True).order_by("priority")

    if not rules.exists():
        logger.info("apply_rules: Geen actieve regels gevonden.")
        return ApplyRulesResult(
            mappings_created=0,
            mappings_skipped_manual=0,
            unique_activities_processed=0,
        )

    # Filter UniqueActivities op datum (via block.date)
    unique_activities = UniqueActivity.objects.all()
    if date_from or date_to:
        if date_from:
            unique_activities = unique_activities.filter(block__date__gte=date_from)
        if date_to:
            unique_activities = unique_activities.filter(block__date__lte=date_to)

    unique_activities = unique_activities.order_by("block__date", "block__started_at")

    mappings_created = 0
    mappings_skipped_manual = 0
    unique_activities_processed = 0

    for ua in unique_activities:
        unique_activities_processed += 1

        # Controleer of er al een handmatige mapping bestaat
        manual_mapping = ActivityMapping.objects.filter(
            unique_activity=ua,
            source=ActivityMapping.SOURCE_MANUAL,
        ).exists()

        if manual_mapping:
            mappings_skipped_manual += 1
            # Handmatige mapping: skip deze activiteit
            continue

        # Loop through regels op prioriteit
        matched_rule = None
        for rule in rules:
            # Check of regel matcht op WindowActivity-velden
            # We controleren de FirstWindowActivity in de UniqueActivity
            window_activity = ua.occurrences.first()
            if window_activity and rule.apply(window_activity):
                matched_rule = rule
                break

        # Bij match: maak TimeEntry en ActivityMapping aan
        if matched_rule:
            # Haal of maak TimeEntry aan voor deze dag en project
            time_entry, _ = TimeEntry.objects.get_or_create(
                project=matched_rule.project,
                date=ua.block.date,
                defaults={"duration_minutes": 0},  # Placeholder, wordt aangepast
            )

            # Controleer of mapping al naar het juiste time_entry wijst
            existing_mapping = ActivityMapping.objects.filter(
                unique_activity=ua,
                time_entry=time_entry,
                source=ActivityMapping.SOURCE_RULE,
            ).exists()

            if not existing_mapping:
                # Verwijder rule-gebaseerde mappings naar andere projecten
                # (zodat we oude rule-matches niet behouden als regel verandert)
                ActivityMapping.objects.filter(
                    unique_activity=ua,
                    source=ActivityMapping.SOURCE_RULE,
                ).exclude(
                    time_entry=time_entry
                ).delete()

                # Maak ActivityMapping aan
                ActivityMapping.objects.create(
                    unique_activity=ua,
                    time_entry=time_entry,
                    source=ActivityMapping.SOURCE_RULE,
                )
                mappings_created += 1

            logger.debug(
                "apply_rules: %s → %s (regel #%d)",
                ua.raw_title[:40],
                matched_rule.project.name,
                matched_rule.id,
            )

    logger.info(
        "apply_rules: %d mappings aangemaakt, %d handmatige overgeslagen, "
        "%d activiteiten verwerkt",
        mappings_created,
        mappings_skipped_manual,
        unique_activities_processed,
    )

    return ApplyRulesResult(
        mappings_created=mappings_created,
        mappings_skipped_manual=mappings_skipped_manual,
        unique_activities_processed=unique_activities_processed,
    )
