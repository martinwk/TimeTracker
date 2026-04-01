# Migration: Update unique_together and remove old activity field

from django.db import migrations, models
import django.db.models.deletion


def set_null_activity(apps, schema_editor):
    """Zet alle activity velden naar NULL voordat we het veld verwijderen."""
    ActivityMapping = apps.get_model('projects', 'ActivityMapping')
    ActivityMapping.objects.all().update(activity=None)


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_populate_unique_activity'),
    ]

    operations = [
        migrations.RunPython(set_null_activity),
        # First remove the old unique_together
        migrations.AlterUniqueTogether(
            name='activitymapping',
            unique_together=set(),
        ),
        # Then remove the activity field
        migrations.RemoveField(
            model_name='activitymapping',
            name='activity',
        ),
        # Finally set the new unique_together
        migrations.AlterUniqueTogether(
            name='activitymapping',
            unique_together={('unique_activity', 'time_entry')},
        ),
    ]

