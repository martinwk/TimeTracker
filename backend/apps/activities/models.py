import re

from django.core.exceptions import ValidationError
from django.db import models


NOISE_TITLES = {
    "idle",
    "program manager",
    "task switching",
    "desktop",
    "untitled",
    "notepad",
}

NOISE_APPS = {
    "program manager",
    "task switching",
}


def extract_app_name(raw_title: str) -> str:
    """
    Extraheert de applicatienaam uit een AHK-venstertitel.

    AHK schrijft titels als:  "Documentnaam - Applicatienaam"
    of:                        "Paginatitel — Mozilla Firefox"
    of:                        "Applicatienaam" (geen scheidingsteken)

    We pakken het deel ná het laatste " - " of " — ".
    """
    for sep in (" — ", " - "):
        if sep in raw_title:
            return raw_title.rsplit(sep, 1)[-1].strip()
    return raw_title.strip()


def detect_noise(raw_title: str) -> bool:
    """
    Geeft True als deze activiteit als ruis beschouwd moet worden.
    Ruis verschijnt standaard niet in de UI maar wordt niet verwijderd.
    """
    lower = raw_title.strip().lower()
    if lower in NOISE_TITLES:
        return True
    app = extract_app_name(raw_title).lower()
    if app in NOISE_APPS:
        return True
    return False


class WindowActivity(models.Model):
    """
    Eén regel uit het AHK-logbestand.
    Wordt bij import aangemaakt en daarna niet meer gewijzigd,
    behalve het veld is_noise.

    Na aggregatie verwijst unique_activity terug naar de UniqueActivity
    waar deze regel toe behoort. Null zolang nog niet geaggregeerd.
    """

    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField()
    duration_seconds = models.PositiveIntegerField()
    raw_title = models.TextField(
        help_text="Originele venstertitel zoals AHK die heeft vastgelegd."
    )
    app_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Geëxtraheerde applicatienaam (deel na het laatste ' - ').",
    )
    date = models.DateField(db_index=True)
    is_noise = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Automatisch True voor Idle, Program Manager, Task Switching, etc. "
            "Kan handmatig worden omgezet. Ruisregels zijn verborgen in de UI."
        ),
    )
    unique_activity = models.ForeignKey(
        "UniqueActivity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="occurrences",
        help_text="De UniqueActivity waar deze regel na aggregatie toe behoort.",
    )

    class Meta:
        ordering = ["started_at"]
        verbose_name = "vensteractiviteit"
        verbose_name_plural = "vensteractiviteiten"

    def __str__(self):
        return f"{self.started_at:%Y-%m-%d %H:%M} | {self.app_name} | {self.raw_title[:60]}"

    @classmethod
    def from_log_line(cls, started_at, ended_at, raw_title):
        """
        Factory-methode: maak een (nog niet opgeslagen) instantie
        op basis van de geparseerde velden uit het logbestand.
        Vult app_name, date en is_noise automatisch in.
        """
        duration = int((ended_at - started_at).total_seconds())
        return cls(
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=max(duration, 0),
            raw_title=raw_title,
            app_name=extract_app_name(raw_title),
            date=started_at.date(),
            is_noise=detect_noise(raw_title),
        )


class ActivityBlock(models.Model):
    """
    Geaggregeerde weergave van WindowActivity-regels binnen een tijdvenster.

    Meerdere korte activiteiten van dezelfde app binnen `block_minutes`
    minuten worden samengevoegd tot één blok.

    De unieke titels binnen een blok zijn beschikbaar via:
        block.unique_activities.all()

    De dominant_title kan achteraf worden bepaald via:
        block.unique_activities.order_by('-total_seconds').first().raw_title

    Wordt aangemaakt door: python manage.py aggregate_activities
    Kan opnieuw worden gegenereerd zonder dataverlies — de ruwe
    WindowActivity records blijven altijd intact.

    project: FK naar Project. Kan handmatig of automatisch worden ingesteld
    via ActivityRule. Nullable tot ActivityRule is aangepast.
    """

    app_name = models.CharField(max_length=255, db_index=True)
    date = models.DateField(db_index=True)
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField()
    total_seconds = models.PositiveIntegerField(
        help_text="Opgetelde actieve seconden van alle onderliggende WindowActivity-regels."
    )
    activity_count = models.PositiveIntegerField(
        help_text="Aantal WindowActivity-regels samengevoegd in dit blok."
    )
    block_minutes = models.PositiveSmallIntegerField(
        help_text="Tijdvenster in minuten waarbinnen activiteiten zijn samengevoegd."
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_blocks",
        help_text="Project waaraan dit blok is toegewezen (handmatig of automatisch via regel).",
    )

    class Meta:
        ordering = ["started_at"]
        verbose_name = "activiteitsblok"
        verbose_name_plural = "activiteitsblokken"

    def __str__(self):
        minutes, seconds = divmod(self.total_seconds, 60)
        return (
            f"{self.started_at:%Y-%m-%d %H:%M} | {self.app_name} | "
            f"{minutes}m {seconds:02d}s | {self.activity_count} activiteiten"
        )

    @property
    def total_minutes(self):
        return round(self.total_seconds / 60, 1)

    @property
    def dominant_title(self):
        """De titel met de meeste cumulatieve seconden in dit blok."""
        ua = self.unique_activities.first()
        return ua.raw_title if ua else None

    def get_recent_project_for_app(self, days_back=30):
        """
        Geeft het meest recent toegewezen project voor hetzelfde app_name.

        Args:
            days_back: Hoeveel dagen terug zoeken in de geschiedenis.

        Returns:
            Project object of None.
        """
        from datetime import timedelta
        from django.utils import timezone

        cutoff_date = self.date - timedelta(days=days_back)
        recent_block = ActivityBlock.objects.filter(
            app_name=self.app_name,
            project__isnull=False,
            date__gte=cutoff_date,
            date__lt=self.date,
        ).order_by("-date").first()

        return recent_block.project if recent_block else None

    def get_project_for_dominant_activity(self):
        """
        Geeft het project dat eerder aan deze dominant activity title
        werd gekoppeld (meest voorkomend project in geschiedenis).

        Returns:
            Project object of None.
        """
        dominant = self.dominant_title
        if not dominant:
            return None

        # Find all blocks with same dominant title that have a project
        from django.db.models import Count

        history = ActivityBlock.objects.filter(
            unique_activities__raw_title=dominant,
            project__isnull=False,
            date__lt=self.date,  # Only past blocks
        ).values("project").annotate(
            count=Count("project")
        ).order_by("-count").first()

        if history:
            from apps.projects.models import Project
            return Project.objects.get(pk=history["project"])
        return None


class UniqueActivity(models.Model):
    """
    Eén unieke venstertitel binnen een ActivityBlock, met de cumulatieve
    tijd dat die titel actief was in het blok.

    Relaties:
        block       → het ActivityBlock waar deze titel toe behoort
        occurrences → de individuele WindowActivity-regels met deze titel
                      (via FK op WindowActivity, één activiteit hoort
                       maar bij één UniqueActivity)

    De cumulatieve tijd (total_seconds) is de som van duration_seconds
    van alle gekoppelde WindowActivity-regels.
    """

    block = models.ForeignKey(
        ActivityBlock,
        on_delete=models.CASCADE,
        related_name="unique_activities",
    )
    raw_title = models.TextField(
        help_text="De venstertitel waarop gegroepeerd is."
    )
    total_seconds = models.PositiveIntegerField(
        help_text="Cumulatieve actieve tijd voor deze titel binnen het blok."
    )

    class Meta:
        ordering = ["-total_seconds"]
        verbose_name = "unieke activiteit"
        verbose_name_plural = "unieke activiteiten"

    def __str__(self):
        minutes, seconds = divmod(self.total_seconds, 60)
        return f"{minutes}m {seconds:02d}s | {self.raw_title[:80]}"

    @property
    def total_minutes(self):
        return round(self.total_seconds / 60, 1)


class ActivityRule(models.Model):
    """
    Een automatische koppelregel: als een WindowActivity aan het patroon
    voldoet, wordt hij aan het opgegeven project gekoppeld.

    match_field bepaalt wát we controleren; match_value is het patroon.

    Uitbreiden naar regex: voeg 'title_regex' en 'app_regex' toe aan
    MATCH_FIELD_CHOICES. De apply()-methode hoeft dan alleen een extra
    elif-tak te krijgen — geen migraties nodig aan bestaande data.
    """

    MATCH_FIELD_CHOICES = [
        ("app_name", "Applicatienaam (exact, hoofdletterongevoelig)"),
        ("title_contains", "Venstertitel bevat tekst (hoofdletterongevoelig)"),
        ("dominant_activity", "Dominante activity-titel geschiedenis"),
        ("recent_project", "Recent gebruikt project voor deze app"),
        # Toekomstige opties — oncommentarieer en migreer wanneer nodig:
        # ("title_regex", "Venstertitel (reguliere expressie)"),
        # ("app_regex",   "Applicatienaam (reguliere expressie)"),
    ]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="rules",
    )
    match_field = models.CharField(max_length=30, choices=MATCH_FIELD_CHOICES)
    match_value = models.CharField(
        max_length=255,
        help_text="Waarde om op te matchen (hoofdletterongevoelig).",
    )
    priority = models.PositiveSmallIntegerField(
        default=10,
        help_text=(
            "Lagere waarde = hogere prioriteit. "
            "Bij meerdere matchende regels wint de laagste priority-waarde."
        ),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["priority", "id"]
        verbose_name = "activiteitsregel"
        verbose_name_plural = "activiteitsregels"

    def __str__(self):
        return (
            f"[prio {self.priority}] {self.get_match_field_display()} "
            f"= '{self.match_value}' → {self.project.name}"
        )

    def clean(self):
        """Valideer het patroon op het moment dat de regel wordt opgeslagen."""
        if self.match_field in ("title_regex", "app_regex"):
            try:
                re.compile(self.match_value)
            except re.error as exc:
                raise ValidationError(
                    {"match_value": f"Ongeldige reguliere expressie: {exc}"}
                )

    def apply(self, activity: "WindowActivity") -> bool:
        """
        Geeft True als deze regel van toepassing is op de gegeven activiteit.
        Voeg hier toekomstige match_field-typen toe als extra elif-tak.
        """
        val = self.match_value.lower()

        if self.match_field == "app_name":
            return activity.app_name.lower() == val

        if self.match_field == "title_contains":
            return val in activity.raw_title.lower()

        if self.match_field == "dominant_activity":
            # match_value should be the exact dominant activity title
            if hasattr(activity, 'unique_activity') and activity.unique_activity:
                return activity.unique_activity.raw_title.lower() == val.lower()
            return False

        if self.match_field == "recent_project":
            # match_value should be "app_name" - this rule matches if app_name matches
            # and there's a recent project history for this app
            return activity.app_name.lower() == val.lower()

        # Toekomstige regex-opties:
        # if self.match_field == "title_regex":
        #     return bool(re.search(self.match_value, activity.raw_title, re.IGNORECASE))
        # if self.match_field == "app_regex":
        #     return bool(re.search(self.match_value, activity.app_name, re.IGNORECASE))

        return False


class BlockProjectHistory(models.Model):
    """
    Geschiedenis van project-toewijzingen aan activity blocks.

    Gebruikt om intelligent project-suggestions te genereren op basis van:
    - Hoe vaak een project voor een bepaalde app wordt gebruikt
    - Hoe recent een project voor een app is gebruikt
    - Welk project het meest voorkomt voor een bepaalde activity title

    Dit model wordt automatisch gevuld als blocks een project krijgen
    (via regel of handmatig).
    """

    block = models.ForeignKey(
        ActivityBlock,
        on_delete=models.CASCADE,
        related_name="project_assignments",
        help_text="Het ActivityBlock dat aan een project is toegewezen.",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="block_assignments",
        help_text="Het project waartoe het block is toegewezen.",
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp van de toewijzing.",
    )
    assigned_by = models.CharField(
        max_length=20,
        choices=[
            ("rule", "Automatische regel"),
            ("manual", "Handmatig door gebruiker"),
        ],
        default="rule",
        help_text="Hoe de toewijzing tot stand is gekomen.",
    )

    class Meta:
        ordering = ["-assigned_at"]
        verbose_name = "block-project geschiedenis"
        verbose_name_plural = "block-project geschiedenissen"
        indexes = [
            models.Index(fields=["block", "-assigned_at"]),
            models.Index(fields=["project", "-assigned_at"]),
        ]

    def __str__(self):
        return (
            f"{self.block.app_name} ({self.block.date}) → "
            f"{self.project.name} ({self.get_assigned_by_display()})"
        )