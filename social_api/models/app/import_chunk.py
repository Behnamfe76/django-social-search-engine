from django.db import models


class ImportChunk(models.Model):
    """A record-aligned byte range of the uploaded file, processed by one task.

    Chunks address the source by offset instead of carrying rows in the message
    body: a single profile in this dataset reaches 53 KB, so a few hundred of them
    inline would put multi-megabyte payloads on the broker. ``seek(start); read(n)``
    is also exactly an S3 ranged GET, which is what makes the storage backend
    swappable.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    # A task may only claim a chunk sitting in one of these; that conditional
    # UPDATE is what makes redelivery safe.
    CLAIMABLE_STATUSES = (Status.PENDING, Status.FAILED)

    id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(
        "ImportBatch",
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    index = models.PositiveIntegerField()
    start_offset = models.BigIntegerField()
    end_offset = models.BigIntegerField()
    # 1-based position of this chunk's first data row within the whole file, so a
    # row error can be reported against the source rather than against the chunk.
    first_row = models.PositiveIntegerField(default=1)
    row_count = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    processed_rows = models.IntegerField(default=0)
    created_rows = models.IntegerField(default=0)
    updated_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    error = models.TextField(null=True, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "import_chunks"
        ordering = ("batch", "index")
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "index"],
                name="import_chunks_batch_index_uniq",
            ),
        ]

    def __str__(self):
        return f"batch {self.batch_id} chunk {self.index}"

    @property
    def byte_length(self):
        return self.end_offset - self.start_offset
