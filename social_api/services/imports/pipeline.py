"""Import orchestration: plan, process, finalise.

Deliberately free of any Celery import, so the whole pipeline can be exercised
without a broker. ``social_api.tasks.imports`` is a thin wrapper that adds retries
and hands work to the queue.

Every stage begins by *claiming* its row with a conditional UPDATE. That single
atomic statement is what makes the pipeline safe under a broker that guarantees
at-least-once delivery: a redelivered message finds nothing to claim and returns.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from social_api.models import ImportBatch, ImportChunk, ImportRowError
from social_api.services.imports import dispatch
from social_api.services.imports.chunking import plan_chunks
from social_api.services.imports.reader import iter_rows, read_range
from social_api.services.imports.row_importer import ChunkImporter

logger = logging.getLogger(__name__)

CHUNK_INSERT_BATCH = 500
ERROR_MESSAGE_LIMIT = 2000


def plan_batch(batch_id):
    """Scan the upload into chunk rows, then dispatch a task per chunk."""
    claimed = ImportBatch.objects.filter(
        pk=batch_id, status=ImportBatch.Status.PENDING
    ).update(status=ImportBatch.Status.PLANNING, started_at=timezone.now())
    if not claimed:
        logger.info("import batch %s already planned; ignoring", batch_id)
        return

    batch = ImportBatch.objects.get(pk=batch_id)
    if not batch.file:
        _fail(batch_id, "batch has no stored file")
        return

    try:
        with transaction.atomic():
            header_end, total_rows, total_chunks = _write_chunks(batch)
            ImportBatch.objects.filter(pk=batch_id).update(
                header_end=header_end,
                row_count=total_rows,
                total_chunks=total_chunks,
                pending_chunks=total_chunks,
                status=ImportBatch.Status.PROCESSING,
            )
            # An empty file leaves pending_chunks at zero, so this claims
            # finalisation immediately; otherwise it is a no-op.
            _claim_finalisation(batch_id)
            transaction.on_commit(lambda: _dispatch_chunks(batch_id))
    except Exception as exc:  # noqa: BLE001 - recorded on the batch, then re-raised
        _fail(batch_id, f"{type(exc).__name__}: {exc}")
        raise

    logger.info(
        "planned import batch %s: %s rows in %s chunks", batch_id, total_rows, total_chunks
    )


def _write_chunks(batch):
    """Stream the file once, writing chunk rows as they are discovered."""
    total_rows = 0
    total_chunks = 0
    pending = []

    with batch.file.open("rb") as handle:
        header_end, spans = plan_chunks(
            handle,
            target_bytes=settings.IMPORT_CHUNK_TARGET_BYTES,
            max_rows=settings.IMPORT_CHUNK_MAX_ROWS,
            block_size=settings.IMPORT_SCAN_BLOCK_BYTES,
        )
        for span in spans:
            pending.append(
                ImportChunk(
                    batch=batch,
                    index=span.index,
                    start_offset=span.start,
                    end_offset=span.end,
                    first_row=span.first_row,
                    row_count=span.row_count,
                )
            )
            total_rows += span.row_count
            total_chunks += 1
            # Chunk rows are flushed in batches so planning a very large file does
            # not accumulate the whole plan in memory either.
            if len(pending) >= CHUNK_INSERT_BATCH:
                ImportChunk.objects.bulk_create(pending)
                pending = []

    if pending:
        ImportChunk.objects.bulk_create(pending)

    return header_end, total_rows, total_chunks


def _dispatch_chunks(batch_id):
    chunk_ids = (
        ImportChunk.objects.filter(
            batch_id=batch_id, status=ImportChunk.Status.PENDING
        )
        .order_by("index")
        .values_list("id", flat=True)
    )
    for chunk_id in chunk_ids.iterator(chunk_size=CHUNK_INSERT_BATCH):
        dispatch.process_chunk(chunk_id)


def process_chunk(chunk_id):
    """Import one chunk's byte range. Safe to call twice for the same chunk."""
    claimed = ImportChunk.objects.filter(
        pk=chunk_id, status__in=ImportChunk.CLAIMABLE_STATUSES
    ).update(
        status=ImportChunk.Status.PROCESSING,
        started_at=timezone.now(),
        error=None,
    )
    if not claimed:
        logger.info("import chunk %s already claimed; ignoring", chunk_id)
        return

    chunk = ImportChunk.objects.select_related("batch").get(pk=chunk_id)
    batch = chunk.batch

    try:
        # One transaction for the whole chunk: a retry after a crash re-does the
        # chunk from a clean slate, and the counter update below cannot drift from
        # the rows it is counting.
        with transaction.atomic():
            result = _import_chunk(chunk, batch)
            _record_chunk(chunk, batch, result)
    except Exception:
        ImportChunk.objects.filter(pk=chunk_id).update(
            status=ImportChunk.Status.FAILED, finished_at=timezone.now()
        )
        raise


def _import_chunk(chunk, batch):
    storage = batch.file.storage
    name = batch.file.name
    header = read_range(storage, name, 0, batch.header_end)
    body = read_range(storage, name, chunk.start_offset, chunk.end_offset)

    rows = iter_rows(header, body, first_row=chunk.first_row)
    return ChunkImporter(batch).run(rows)


def _record_chunk(chunk, batch, result):
    ImportRowError.objects.bulk_create(
        [
            ImportRowError(
                batch=batch,
                chunk=chunk,
                row_number=number,
                message=(message or "")[:ERROR_MESSAGE_LIMIT],
                excerpt=excerpt or "",
            )
            for number, message, excerpt in result.errors
        ]
    )

    ImportChunk.objects.filter(pk=chunk.pk).update(
        status=ImportChunk.Status.COMPLETED,
        processed_rows=result.processed,
        created_rows=result.created,
        updated_rows=result.updated,
        failed_rows=result.failed,
        finished_at=timezone.now(),
    )

    _advance_batch(
        batch.pk,
        processed=result.processed,
        created=result.created,
        updated=result.updated,
        failed=result.failed,
    )


def abandon_chunk(chunk_id, reason):
    """Give up on a chunk whose retries are exhausted, without stalling the batch.

    The chunk's rows are counted as failed so ``pending_chunks`` still reaches
    zero and the batch can reach a terminal state.
    """
    chunk = ImportChunk.objects.select_related("batch").filter(pk=chunk_id).first()
    if chunk is None or chunk.status == ImportChunk.Status.COMPLETED:
        return

    message = f"{type(reason).__name__}: {reason}"[:ERROR_MESSAGE_LIMIT]
    with transaction.atomic():
        ImportRowError.objects.create(
            batch=chunk.batch,
            chunk=chunk,
            row_number=chunk.first_row,
            message=f"chunk abandoned after repeated failures -- {message}",
        )
        ImportChunk.objects.filter(pk=chunk_id).update(
            status=ImportChunk.Status.FAILED,
            error=message,
            failed_rows=chunk.row_count,
            processed_rows=chunk.row_count,
            finished_at=timezone.now(),
        )
        _advance_batch(chunk.batch_id, processed=chunk.row_count, failed=chunk.row_count)

    logger.error("abandoned import chunk %s: %s", chunk_id, message)


def _advance_batch(batch_id, *, processed=0, created=0, updated=0, failed=0):
    """Fold one chunk's totals into the batch and hand over the fan-in baton."""
    ImportBatch.objects.filter(pk=batch_id).update(
        processed_rows=F("processed_rows") + processed,
        created_rows=F("created_rows") + created,
        updated_rows=F("updated_rows") + updated,
        failed_rows=F("failed_rows") + failed,
        pending_chunks=F("pending_chunks") - 1,
    )
    _claim_finalisation(batch_id)


def _claim_finalisation(batch_id):
    """Exactly one caller wins this UPDATE, and it is the one that finalises."""
    claimed = ImportBatch.objects.filter(
        pk=batch_id,
        pending_chunks__lte=0,
        status__in=(ImportBatch.Status.PLANNING, ImportBatch.Status.PROCESSING),
    ).update(status=ImportBatch.Status.FINALISING)
    if claimed:
        transaction.on_commit(lambda: dispatch.finalise_batch(batch_id))


def finalise_batch(batch_id):
    """Close the batch out and drop the upload."""
    batch = ImportBatch.objects.filter(pk=batch_id).first()
    if batch is None or batch.is_terminal:
        return

    status = (
        ImportBatch.Status.PARTIAL
        if batch.failed_rows
        else ImportBatch.Status.COMPLETED
    )
    deleted = _delete_upload(batch)

    ImportBatch.objects.filter(pk=batch_id).update(
        status=status,
        finished_at=timezone.now(),
        **({"file": ""} if deleted else {}),
    )
    logger.info(
        "finished import batch %s as %s (%s failed rows)",
        batch_id,
        status,
        batch.failed_rows,
    )


def _delete_upload(batch):
    """Remove the stored file. Kept on hard failure so a batch can be re-run."""
    if not settings.IMPORT_DELETE_FILE_WHEN_DONE or not batch.file:
        return False
    try:
        batch.file.delete(save=False)
    except OSError as exc:
        logger.warning("could not delete upload for batch %s: %s", batch.pk, exc)
        return False
    return True


def _fail(batch_id, message):
    ImportBatch.objects.filter(pk=batch_id).update(
        status=ImportBatch.Status.FAILED,
        error=message[:ERROR_MESSAGE_LIMIT],
        finished_at=timezone.now(),
    )
    logger.error("import batch %s failed: %s", batch_id, message)
