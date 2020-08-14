from asyncio import CancelledError, get_event_loop
import ast
import json
import logging
from traceback import format_exc

from ..backend import SessionManager


_log = logging.getLogger(__name__)


def prompt_print(*args, **kwargs):
    aprint(*args, **kwargs, end='')


def print_result(msg, prompt):
    debug_log_msg(msg)
    aprint(msg['content']['data']['text/plain'])
    prompt_print(prompt)


def print_stream(msg, prompt):
    debug_log_msg(msg)
    aprint()
    aprint(msg['content']['text'], end='')
    prompt_print(prompt)


def print_exception(msg, prompt):
    debug_log_msg(msg)
    aprint('\n'.join(msg['content']['traceback']))
    prompt_print(prompt)


def aprint(*args, **kwargs):
    print(*args, **kwargs, flush=True)


def debug_log_msg(msg):
    if _log.getEffectiveLevel() <= logging.DEBUG:
        _log.debug(f'interpreter response message:\n{msg}')


def nullfunc(*_, **__):
    pass


def readline_from_fd(queue, fd):
    queue.put_nowait(fd.readline())


class ActiveSessionManager(SessionManager):
    async def execute(self, code):
        return await super().execute(code, name=self.active)


class StateManager:
    default_session = 'default'
    msg_printer = {
        'status': nullfunc,
        'execute_input': nullfunc,
        'execute_result': print_result,
        'execute_reply': nullfunc,
        'stream': print_stream,
        'error': print_exception,
    }

    def __init__(self):
        self.sm = ActiveSessionManager()
        self.state = NoStateDispatcher()
        self._listener = get_event_loop().create_task(self._listen())

    async def start(self):
        await self.sm.start_session(self.default_session)
        self.sm.active = self.default_session

    async def shutdown(self):
        await self.sm.stop_all()
        if not self._listener.done():
            self._listener.cancel()
            await self._listener

    async def process_input(self, text):
        self.state = await self.state.process(self, text)
        prompt_print(self.state.prompt)

    async def _listen(self):
        try:
            async for msg in self.sm:
                printer = self.msg_printer.get(msg['msg_type'])
                if printer is None:
                    printer = lambda m, p: prompt_print(f'{m}\n{p}')
                printer(msg, self.state.prompt)
        except CancelledError:
            pass


class NoStateDispatcher:
    prompt = ">>> "

    async def process(self, state, text):
        if not text.strip():
            return self

        if len(text) and text[0] == '%':
            return await SpecialCommandProcessor().process(state, text)
        return await PythonProcessor().process(state, text)


class PythonProcessor:
    prompt = "... "

    def __init__(self):
        self.lines = []

    async def process(self, state, text):
        if not len(self.lines):
            return await self.process_first_line(state, text)
        return await self.process_next_line(state, text)

    async def process_first_line(self, state, text):
        try:
            ast.parse(text)
        except Exception as e:
            if 'EOF' in str(e):
                self.lines.append(text)
                return self
            aprint(format_exc())
        else:
            await state.sm.execute(text)
        return NoStateDispatcher()

    async def process_next_line(self, state, text):
        if text.strip():
            self.lines.append(text)
            return self
        await state.sm.execute(''.join(self.lines))
        return NoStateDispatcher()


class SessionSwitcher:
    async def process(self, state, text):
        new_session_name = text.split()[0:]
        if not new_session_name:
            return await SessionHelp().process(state, text)
        new_session_name = new_session_name[0]
        await state.sm.start_session(new_session_name)
        state.sm.active = new_session_name
        return NoStateDispatcher()


class SessionHelp:
    async def process(self, state, text):
        aprint("commands:")
        aprint("%help - this message")
        aprint("%switch - switch to a new python interpeter session")
        aprint("%name - name of current session")
        return NoStateDispatcher()


class SessionName:
    async def process(self, state, text):
        aprint(f"Name: {state.sm.active}")
        return NoStateDispatcher()


class SpecialCommandProcessor:
    commands = {
        '%help': SessionHelp,
        '%switch': SessionSwitcher,
        '%name': SessionName,
    }
    async def process(self, state, text):
        cmd, *remainder = text.split(maxsplit=1)
        try:
            processor = self.commands[cmd]
        except KeyError:
            processor = SessionHelp
        return await processor().process(state, ''.join(remainder))


async def main(queue):
    processor = StateManager()
    await processor.start()
    while True:
        text = await queue.get()

        if not len(text):
            await processor.shutdown()
            aprint()
            return

        await processor.process_input(text)


def setup_logging(verbosity):
    level = logging.ERROR - 10*verbosity
    logging.basicConfig(level=level)


if __name__ == '__main__':
    from argparse import ArgumentParser
    from asyncio import Queue
    from sys import stdin
    import threading

    p = ArgumentParser(description='Test console multi-Python interface.')
    p.add_argument('-v', action='count', default=0,
                   help='verbose (specify multiple times for more verbosity)')
    args = p.parse_args()
    setup_logging(args.v)

    queue = Queue()
    loop = get_event_loop()
    loop.add_reader(stdin, readline_from_fd, queue, stdin)

    print("Multi-interpreter Python REPL")
    print("Type '%help' for session commands")
    prompt_print(NoStateDispatcher.prompt)
    loop.run_until_complete(main(queue))
    threading.active_count()
