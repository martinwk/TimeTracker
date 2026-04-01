# Generated migration: Add unique_activity FK field to ActivityMapping

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_alter_activitymapping_options'),
        ('activities', '0005_remove_uniqueactivity_occurrences_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitymapping',
            name='unique_activity',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='mappings',
                to='activities.uniqueactivity'
            ),
        ),
        migrations.AlterField(
            model_name='activitymapping',
            name='activity',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='mappings',
                to='activities.windowactivity'
            ),
        ),
    ]
