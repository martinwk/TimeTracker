from django.core.validators import MinValueValidator
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
        Geeft het totaal aantal geboekte minuten, optioneel gefilterd op datum.
        Handig in de API zonder extra annotatie-query.
        """
        qs = self.time_entries.all()
        if date:
            qs = qs.filter(date=date)
        result = qs.aggregate(total=models.Sum("duration_minutes"))
        return result["total"] or 0


class TimeEntry(models.Model):
    """
    Een handmatig ingevoerde (of bevestigde) tijdregistratie:
    X minuten aan project Y op datum Z.

    Dit is de bron van waarheid voor urenstaten.
    WindowActivity-regels kunnen een TimeEntry *voorstellen*,
    maar een mens bevestigt of corrigeert altijd.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,   # voorkom per ongeluk verwijderen van projecten met uren
        related_name="time_entries",
    )
    date = models.DateField(db_index=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Aantal minuten besteed aan dit project op deze datum.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "project__name"]
        verbose_name = "tijdregistratie"
        verbose_name_plural = "tijdregistraties"

    def __str__(self):
        hours, mins = divmod(self.duration_minutes, 60)
        return f"{self.date} | {self.project.name} | {hours}u {mins:02d}m"

    @property
    def duration_hours(self):
        return round(self.duration_minutes / 60, 2)


class ActivityMapping(models.Model):
    """
    Koppeling tussen een UniqueActivity en een TimeEntry.

    source geeft aan hoe de koppeling tot stand is gekomen:
      'rule'   — automatisch aangemaakt door een ActivityRule
      'manual' — handmatig gezet door de gebruiker in de UI

    Een activiteit kan aan meerdere TimeEntries hangen (split-dag),
    maar in de praktijk is 1-op-1 de norm.
    """

    SOURCE_RULE = "rule"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_RULE, "Automatisch (regel)"),
        (SOURCE_MANUAL, "Handmatig"),
    ]

    unique_activity = models.ForeignKey(
        "activities.UniqueActivity",
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    time_entry = models.ForeignKey(
        TimeEntry,
        on_delete=models.CASCADE,
        related_name="activity_mappings",
    )
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=SOURCE_RULE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Één unieke activiteit mag maar één keer aan dezelfde TimeEntry hangen
        unique_together = [("unique_activity", "time_entry")]
        ordering = ["unique_activity__block__started_at"]
        verbose_name = "activiteitskoppeling"
        verbose_name_plural = "activiteitskoppelingen"

    def __str__(self):
        return (
            f"{self.unique_activity.raw_title[:40]} → {self.time_entry.project.name} "
            f"({self.get_source_display()})"
        )
