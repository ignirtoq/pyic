from asyncio import Queue

__all__ = ['AiterQueue', 'StoppedQueueError']


class StoppedQueueError(ValueError):
    """The asynchronous queue has been stopped."""


class AiterQueue:
    _sentinel = object()

    def __init__(self):
        self._q = Queue()
        self._stopped = False
        self._active = True

    def stop_nowait(self):
        self._stopped = True
        retval = self._q.put_nowait(self._sentinel)
        return retval

    async def stop(self):
        self._stopped = True
        retval = await self._q.put(self._sentinel)
        return retval

    def put_nowait(self, item):
        if self._stopped:
            raise StoppedQueueError
        return self._q.put_nowait(item)

    async def put(self, item):
        if self._stopped:
            raise StoppedQueueError
        return await self._q.put(item)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._active:
            raise StopAsyncIteration

        item = await self._q.get()
        if item is self._sentinel:
            self._active = False
            raise StopAsyncIteration

        return item
