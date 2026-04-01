# Data migration: Populate unique_activity from activity's unique_activity

from django.db import migrations


def populate_unique_activity(apps, schema_editor):
    """
    Voor elke ActivityMapping: als het een WindowActivity heeft,
    haal de UniqueActivity van dat WindowActivity op en set die.
    """
    ActivityMapping = apps.get_model('projects', 'ActivityMapping')

    for mapping in ActivityMapping.objects.filter(activity__isnull=False):
        # WindowActivity heeft unique_activity FK
        if mapping.activity.unique_activity:
            mapping.unique_activity = mapping.activity.unique_activity
            mapping.save()


def reverse_populate(apps, schema_editor):
    """Reverse: zet unique_activity terug naar NULL."""
    ActivityMapping = apps.get_model('projects', 'ActivityMapping')
    ActivityMapping.objects.all().update(unique_activity=None)


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_activitymapping_unique_activity'),
    ]

    operations = [
        migrations.RunPython(populate_unique_activity, reverse_populate),
    ]
