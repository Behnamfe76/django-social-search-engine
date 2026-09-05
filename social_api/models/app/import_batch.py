import uuid

from django.db import models
from django.utils import timezone


def import_upload_path(instance, filename):
    """Partition uploads by day and keep concurrent uploads from colliding."""
    return f"imports/{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}/{filename}"


class ImportBatch(models.Model):
    """One uploaded dataset, plus the progress of the workers chewing through it.

    The counters double as the fan-in mechanism. ``pending_chunks`` is decremented
    atomically as each chunk task commits, and whichever decrement lands on zero
    claims finalisation with a conditional UPDATE. Completion detection therefore
    lives in the database rather than in a Celery chord: it survives worker
    restarts, needs no result backend, and is the same row the progress endpoint
    reads.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PLANNING = "planning", "Planning"
        PROCESSING = "processing", "Processing"
        FINALISING = "finalising", "Finalising"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Completed with errors"
        FAILED = "failed", "Failed"

    TERMINAL_STATUSES = frozenset(
        {Status.COMPLETED, Status.PARTIAL, Status.FAILED}
    )

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
    # Held through the storage backend rather than a raw path, so pointing
    # production at S3 is a STORAGES setting rather than a code change.
    file = models.FileField(
        upload_to=import_upload_path,
        max_length=500,
        null=True,
        blank=True,
        help_text="Deleted once the batch reaches a terminal state.",
    )
    file_size = models.BigIntegerField(null=True, blank=True)
    # Byte offset just past the header record; workers prepend those bytes to
    # their own slice so each chunk parses as a standalone CSV document.
    header_end = models.BigIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    row_count = models.IntegerField(
        null=True, blank=True, help_text="Data rows found while planning."
    )
    total_chunks = models.IntegerField(default=0)
    pending_chunks = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    created_rows = models.IntegerField(default=0)
    updated_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error = models.TextField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_batches"
        verbose_name_plural = "import batches"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.source}: {self.filename}"

    @property
    def is_terminal(self):
        return self.status in self.TERMINAL_STATUSES

    @property
    def progress(self):
        """Percent of planned rows the workers have accounted for."""
        if self.status in (self.Status.COMPLETED, self.Status.PARTIAL):
            return 100.0
        if not self.row_count:
            return 0.0
        done = min(self.processed_rows / self.row_count, 1.0)
        return round(done * 100, 2)

    @property
    def duration_seconds(self):
        if self.started_at is None:
            return None
        end = self.finished_at or timezone.now()
        return round((end - self.started_at).total_seconds(), 3)
