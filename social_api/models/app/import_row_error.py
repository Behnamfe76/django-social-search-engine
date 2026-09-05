from django.db import models


class ImportRowError(models.Model):
    """A single source row the importer could not take.

    Kept per row rather than failing the batch: the sample export alone carries 53
    rows whose column count does not match the header, and losing 283 good profiles
    to fix 53 bad ones is the wrong trade.
    """

    EXCERPT_LIMIT = 500

    id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(
        "ImportBatch",
        on_delete=models.CASCADE,
        related_name="row_errors",
    )
    chunk = models.ForeignKey(
        "ImportChunk",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="row_errors",
    )
    row_number = models.PositiveIntegerField(
        help_text="1-based data row within the source file."
    )
    message = models.TextField()
    excerpt = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_row_errors"
        ordering = ("batch", "row_number")
        indexes = [
            models.Index(fields=["batch", "row_number"], name="import_row_errors_idx"),
        ]

    def __str__(self):
        return f"batch {self.batch_id} row {self.row_number}: {self.message}"
