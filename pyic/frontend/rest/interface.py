from abc import ABCMeta, abstractmethod
from asyncio import CancelledError, Future, get_event_loop
import logging

from aiohttp import web

from .adapter import SESSION_MANAGER, SESSION_RESPONSES, attach_backend

__all__ = [
    'RestSessions',
    'VerificationError',
]

_log = logging.getLogger(__name__)


class VerificationError(ValueError):
    """Problem verifying authenticity of the request origin."""


class RestSessions(web.View, metaclass=ABCMeta):

    # Required definitions

    @abstractmethod
    async def process_request(self, body):
        pass

    @classmethod
    @abstractmethod
    def add_app_routes(cls, app, **cmdargs):
        pass

    # Optional definitions

    async def verify_request(self, body):
        pass

    @classmethod
    def setup_app(cls, app):
        pass

    # Support methods

    async def execute(self, session, codeblock, handler):
        sm = self.request.app[SESSION_MANAGER]
        future_map = self.request.app[SESSION_RESPONSES]

        await sm.start_session(session)
        msg_id = await sm.execute(codeblock, name=session)

        future = Future()
        future_map[msg_id] = future

        get_event_loop().create_task(
            self._listen_for_interpreter_response(msg_id, future_map, handler))

    @classmethod
    def get_app(cls):
        app = web.Application()
        attach_backend(app)
        cls.setup_app(app)
        return app

    # Implementation

    async def post(self):
        try:
            return await self._handle_request()
        except VerificationError as e:
            err = f'error verifying origin, ignoring request: {e.args[0]}'
            _log.warning(err)
            raise web.HTTPUnauthorized from None
        except web.HTTPException:
            raise
        except Exception:
            err = 'unexpected exception'
            _log.exception(err)
            raise web.HTTPInternalServerError from None

    async def _handle_request(self):
        req = self.request
        body = b'' if not req.can_read_body else await req.content.read()

        await self.verify_request(body)

        return await self.process_request(body)

    @classmethod
    async def _listen_for_interpreter_response(cls, msg_id, future_map, handler):
        future = future_map[msg_id]
        try:
            response = await future
        except CancelledError:
            return
        else:
            await handler(response)
        finally:
            try:
                future_map.pop(msg_id)
            except KeyError:
                pass
