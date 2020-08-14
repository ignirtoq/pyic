import pytest

from pyslackapp.backend import _AiterQueue, StoppedQueueError


@pytest.fixture
async def q():
    return _AiterQueue()


@pytest.mark.asyncio
async def test_aiterqueue_iteration(q):
    num_items = 2

    for item in range(num_items):
        q.put_nowait(item)
    q.stop_nowait()

    i = 0
    async for item in q:
        assert item == i
        i += 1


def test_put_stopped_queue(q):
    q.stop_nowait()
    with pytest.raises(StoppedQueueError):
        q.put_nowait(1)
