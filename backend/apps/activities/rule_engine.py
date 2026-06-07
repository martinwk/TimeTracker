"""
Rule engine voor het automatisch koppelen van ActivityBlocks aan projecten.

Algoritme:
  1. Haal alle actieve ActivityRules op, gesorteerd op prioriteit (laag = belangrijk)
  2. Blokken met een handmatige toewijzing (BlockProjectHistory.assigned_by='manual')
     worden overgeslagen — handmatige keuzes worden nooit overschreven.
  3. Blokken met een rule-toewijzing worden wél opnieuw geëvalueerd zodat
     regelwijzigingen doorwerken.
  4. Per block: loop through regels totdat één matcht; wijs toe als het project verandert.
  5. Return statistieken: aangemaakt, skipped, verwerkt.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.db.models import Exists, OuterRef

from apps.activities.models import ActivityRule, ActivityBlock, BlockProjectHistory

logger = logging.getLogger(__name__)


@dataclass
class ApplyRulesResult:
    """Resultaat van apply_rules() operatie."""
    blocks_assigned: int
    blocks_skipped_manual: int
    blocks_processed: int


def apply_rules(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ApplyRulesResult:
    """
    Voer alle actieve ActivityRules toe op ActivityBlocks.

    Blokken met een handmatige toewijzing worden beschermd en overgeslagen.
    Blokken met een rule-toewijzing worden opnieuw geëvalueerd.
    """
    rules = ActivityRule.objects.filter(is_active=True).order_by("priority")

    if not rules.exists():
        logger.info("apply_rules: Geen actieve regels gevonden.")
        return ApplyRulesResult(
            blocks_assigned=0,
            blocks_skipped_manual=0,
            blocks_processed=0,
        )

    # Subquery: heeft dit blok een handmatige toewijzing in de history?
    has_manual_assignment = BlockProjectHistory.objects.filter(
        block=OuterRef("pk"),
        assigned_by="manual",
    )

    date_qs = ActivityBlock.objects.all()
    if date_from:
        date_qs = date_qs.filter(date__gte=date_from)
    if date_to:
        date_qs = date_qs.filter(date__lte=date_to)

    blocks_skipped_manual = date_qs.filter(Exists(has_manual_assignment)).count()
    blocks = date_qs.exclude(Exists(has_manual_assignment)).order_by("date", "started_at")

    blocks_assigned = 0
    blocks_processed = 0

    for block in blocks:
        blocks_processed += 1
        matched_project = None

        for rule in rules:
            if rule.match_field == "dominant_activity":
                dominant = block.dominant_title
                if dominant and rule.match_value.lower() == dominant.lower():
                    p = block.get_project_for_dominant_activity()
                    if p:
                        matched_project = p
                        break

            elif rule.match_field == "recent_project":
                if block.app_name.lower() == rule.match_value.lower():
                    p = block.get_recent_project_for_app()
                    if p:
                        matched_project = p
                        break

            else:
                ua = block.unique_activities.first()
                window_activity = ua.occurrences.first() if ua else None
                if window_activity and rule.apply(window_activity):
                    matched_project = rule.project
                    break

        if matched_project and block.project != matched_project:
            block.project = matched_project
            block.save(update_fields=["project"])
            BlockProjectHistory.objects.create(
                block=block,
                project=matched_project,
                assigned_by="rule",
            )
            blocks_assigned += 1
            logger.debug(
                "apply_rules: Block %d (%s) → %s",
                block.id,
                block.dominant_title[:40] if block.dominant_title else "N/A",
                matched_project.name,
            )

    logger.info(
        "apply_rules: %d blokken toegewezen, %d handmatig overgeslagen, %d verwerkt",
        blocks_assigned,
        blocks_skipped_manual,
        blocks_processed,
    )

    return ApplyRulesResult(
        blocks_assigned=blocks_assigned,
        blocks_skipped_manual=blocks_skipped_manual,
        blocks_processed=blocks_processed,
    )
