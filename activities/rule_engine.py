"""
Rule engine voor het automatisch koppelen van ActivityBlocks aan projecten.

Algoritme:
  1. Haal alle actieve ActivityRules op, gesorteerd op prioriteit (laag = belangrijk)
  2. Voor elke ActivityBlock zonder project: loop through regels totdat één matcht
  3. Bij eerste match: stel block.project in met het project van de regel
  4. Handmatig ingestelde projecten worden nooit overschreven
  5. Return statistieken: aangemaakt, skipped, al handmatig
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from activities.models import ActivityRule, ActivityBlock, UniqueActivity

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
    Voer alle actieve ActivityRules toe op ActivityBlocks zonder project.

    Args:
        date_from: Startdatum (inclusief). Geen filter als None.
        date_to: Einddatum (inclusief). Geen filter als None.

    Returns:
        ApplyRulesResult met tellingen

    Gedrag:
      - Alleen blocks zonder project worden verwerkt (project is None)
      - Bij elke block: eerste matchende regel (op prioriteit) wordt gebruikt
      - Block.project wordt ingesteld op het project van de regel
      - Idempotent: meerdere keer draaien geeft dezelfde resultaat
    """
    # Haal active rules op, sorteren op prioriteit (laag eerst)
    rules = ActivityRule.objects.filter(is_active=True).order_by("priority")

    if not rules.exists():
        logger.info("apply_rules: Geen actieve regels gevonden.")
        return ApplyRulesResult(
            blocks_assigned=0,
            blocks_skipped_manual=0,
            blocks_processed=0,
        )

    # Filter ActivityBlocks: alleen degenen zonder project
    blocks = ActivityBlock.objects.filter(project__isnull=True)
    if date_from or date_to:
        if date_from:
            blocks = blocks.filter(date__gte=date_from)
        if date_to:
            blocks = blocks.filter(date__lte=date_to)

    blocks = blocks.order_by("date", "started_at")

    blocks_assigned = 0
    blocks_skipped_manual = 0
    blocks_processed = 0

    for block in blocks:
        blocks_processed += 1

        # Loop through regels op prioriteit
        matched_rule = None
        for rule in rules:
            # Handle special rule types that use block history
            if rule.match_field == "dominant_activity":
                # Check if dominant activity title matches and has project history
                dominant = block.dominant_title
                if dominant and rule.match_value.lower() == dominant.lower():
                    project = block.get_project_for_dominant_activity()
                    if project:
                        block.project = project
                        block.save(update_fields=["project"])
                        from activities.models import BlockProjectHistory
                        BlockProjectHistory.objects.create(
                            block=block,
                            project=project,
                            assigned_by="rule",
                        )
                        blocks_assigned += 1
                        matched_rule = rule
                        break
            
            elif rule.match_field == "recent_project":
                # Check if recent project exists for this app
                val = rule.match_value.lower()
                if block.app_name.lower() == val:
                    project = block.get_recent_project_for_app()
                    if project:
                        block.project = project
                        block.save(update_fields=["project"])
                        from activities.models import BlockProjectHistory
                        BlockProjectHistory.objects.create(
                            block=block,
                            project=project,
                            assigned_by="rule",
                        )
                        blocks_assigned += 1
                        matched_rule = rule
                        break
            
            else:
                # Standard rules: app_name, title_contains, etc.
                window_activity = block.unique_activities.first().occurrences.first()
                if window_activity and rule.apply(window_activity):
                    matched_rule = rule
                    block.project = rule.project
                    block.save(update_fields=["project"])
                    
                    from activities.models import BlockProjectHistory
                    BlockProjectHistory.objects.create(
                        block=block,
                        project=rule.project,
                        assigned_by="rule",
                    )
                    blocks_assigned += 1
                    break

        if matched_rule:
            logger.debug(
                "apply_rules: Block %d (%s) → %s (regel #%d, type: %s)",
                block.id,
                block.dominant_title[:40] if block.dominant_title else "N/A",
                matched_rule.project.name,
                matched_rule.id,
                matched_rule.match_field,
            )

    logger.info(
        "apply_rules: %d blocks toegewezen, %d activiteiten verwerkt",
        blocks_assigned,
        blocks_processed,
    )

    return ApplyRulesResult(
        blocks_assigned=blocks_assigned,
        blocks_skipped_manual=blocks_skipped_manual,
        blocks_processed=blocks_processed,
    )
