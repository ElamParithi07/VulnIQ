import pytest

from ingestion.models import PipelineLock
from ingestion.services.locking import PipelineAlreadyRunningError, acquire_pipeline_lock


@pytest.mark.django_db
def test_lock_is_held_during_the_block_and_released_after():
    with acquire_pipeline_lock():
        lock = PipelineLock.objects.get(pk=1)
        assert lock.is_locked is True
        assert lock.locked_at is not None

    lock = PipelineLock.objects.get(pk=1)
    assert lock.is_locked is False
    assert lock.locked_at is None


@pytest.mark.django_db
def test_second_acquire_while_locked_raises():
    PipelineLock.objects.create(pk=1, is_locked=True)

    with pytest.raises(PipelineAlreadyRunningError):
        with acquire_pipeline_lock():
            pass  # pragma: no cover


@pytest.mark.django_db
def test_lock_is_released_even_when_protected_code_raises():
    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        with acquire_pipeline_lock():
            raise Boom("failure inside pipeline")

    lock = PipelineLock.objects.get(pk=1)
    assert lock.is_locked is False


@pytest.mark.django_db
def test_lock_can_be_reacquired_after_release():
    with acquire_pipeline_lock():
        pass

    with acquire_pipeline_lock():
        lock = PipelineLock.objects.get(pk=1)
        assert lock.is_locked is True
