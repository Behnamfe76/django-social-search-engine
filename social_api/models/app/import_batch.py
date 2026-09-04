from django.db import models


class ImportBatch(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_batches",
    )
    source = models.CharField(max_length=255, help_text="e.g. people-data-labs")
    filename = models.CharField(max_length=255)
    row_count = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_batches"
        verbose_name_plural = "import batches"

    def __str__(self):
        return f"{self.source}: {self.filename}"
