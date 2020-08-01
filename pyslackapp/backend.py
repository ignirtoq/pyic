from asyncio import CancelledError, Queue, get_running_loop
from typing import Union

from jupyter_client import AsyncMultiKernelManager


class NoDefaultSessionError(ValueError):
    """Exception raised when no session name is given and no default session is available"""


class SessionNotFoundError(ValueError):
    """Exception raised when the named session cannot be found."""


class SessionManager:

    def __init__(
        self, *_,
        use_default_session: Union[bool, None] = None,
        **__
    ):
        # defaults
        use_default_session = False if use_default_session is None else use_default_session

        # private members
        self._kernelman = AsyncMultiKernelManager()
        self._default = self._kernelman.new_kernel_id() if use_default_session else None
        self._sessions = {}
        self._queue = _AiterQueue()

    def __aiter__(self):
        return self._queue

    @property
    def sessions(self):
        return list(self._sessions.keys())

    async def start_session(self, name):
        if name in self._sessions:
            return

        kid = await self._kernelman.start_kernel()
        client = self._kernelman.get_kernel(kid).client()
        self._sessions[name] = _Session(client, self._queue)

    async def stop_session(self, name):
        if name not in self._sessions:
            return

        try:
            await self._sessions[name].shutdown()
        finally:
            self._remove_session(name)

    async def stop_all(self):
        await self._reset()

    async def execute(self, code, name=None):
        try:
            session = self._sessions[name]
        except KeyError:
            raise SessionNotFoundError("no session found for name "
                                       f"'{name}'") from None

        return session.execute(code)

    def _remove_session(self, name):
        try:
            self._sessions.pop(name)
        except KeyError:
            pass

    async def _reset(self):
        for session in self._sessions.values():
            await session.shutdown()

        self._sessions = {}
        await self._queue.stop()
        self._queue = _AiterQueue()


class _Session:

    def __init__(self, client, msg_queue):
        self.client = client
        self.client.allow_stdin = False
        self._setup_listeners(client, msg_queue)

    async def shutdown(self):
        for listener in self.listeners:
            if not listener.done() and not listener.cancelled():
                listener.cancel()
                await listener
        await self.client.shutdown(reply=True)

    def execute(self, *args, **kwargs):
        return self.client.execute(*args, **kwargs)

    def _setup_listeners(self, client, msg_queue):
        self.listeners = set()
        get_msg_functions = [
            client.get_iopub_msg,
            client.get_shell_msg,
            client.get_stdin_msg,
        ]
        for get_msg_func in get_msg_functions:
            self._start_listener(self.listeners, get_msg_func, msg_queue)

    @classmethod
    def _start_listener(cls, listeners_set, get_func, msg_queue):
        loop = get_running_loop()
        listeners_set.add(loop.create_task(cls._listen(get_func, msg_queue)))

    @staticmethod
    async def _listen(get_func, msg_queue):
        try:
            while True:
                msg = await get_func()
                await msg_queue.put(msg)
        except CancelledError:
            pass


class _AiterQueue:
    _sentinel = object()

    def __init__(self):
        self._q = Queue()
        self._active = True

    def stop_nowait(self):
        self._q.put_nowait(self._sentinel)

    async def stop(self):
        return await self._q.put(self._sentinel)

    def put_nowait(self, item):
        return self._q.put_nowait(item)

    async def put(self, item):
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
