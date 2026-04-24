from django.db import models


class Project(models.Model):
    """
    Een project waaraan werkuren worden gekoppeld.
    Kleur is bedoeld voor de tijdlijn-UI (hex-waarde, bv. '#4F86C6').
    """

    name = models.CharField(max_length=255, unique=True)
    color = models.CharField(
        max_length=7,
        default="#4F86C6",
        help_text="Hexkleurcode inclusief #, bv. '#4F86C6'.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactieve projecten zijn verborgen bij nieuw invoer maar blijven in de geschiedenis.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "project"
        verbose_name_plural = "projecten"

    def __str__(self):
        return self.name

    def total_minutes(self, date=None):
        """
        Geeft het totaal aantal minuten van alle ActivityBlocks,
        optioneel gefilterd op datum.

        Deze berekening is gebaseerd op activity_blocks in plaats van time_entries,
        omdat in de nieuwe architectuur blokken direct aan projecten worden gekoppeld.
        """
        qs = self.activity_blocks.all()
        if date:
            qs = qs.filter(date=date)
        total_seconds = qs.aggregate(total=models.Sum("total_seconds"))["total"] or 0
        return round(total_seconds / 60, 1)

