from functools import partial
import logging
import json
import re

from aiohttp import web

from ..rest import RestSessions
from .constants import VERIFICATION_SECRET, OAUTH_TOKEN
from .responses import respond
from .verification import verify_signature


__all__ = ['handle_request']


_log = logging.getLogger(__name__)

EVENT = 'event'
EVENT_TYPE = 'type'
EVENT_SUBTYPE = 'subtype'
REQUEST_TYPE = 'type'
CHALLENGE = 'challenge'
MSG_TEXT = 'text'


class SlackPythonSessions(RestSessions):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._request_handlers = {
            'url_verification': self.process_challenge,
            'event_callback': self.process_event_callback,
        }
        self._event_handlers = {
            'message': self.process_base_message,
        }
        self._message_subtype_handlers = {
            None: self.process_new_message,
            'message_changed': self.process_edited_message,
            'message_deleted': anoop,
            'bot_add': anoop,
        }

    async def process_request(self, body):
        body_json = json.loads(body.decode()) if body else {}

        request_type = body_json.get(REQUEST_TYPE)
        handler = self._request_handlers.get(request_type, self.process_unknown_request)

        return await handler(body_json)

    @classmethod
    def add_app_routes(cls, app, *, secret, oauth, **cmdargs):
        app[VERIFICATION_SECRET] = read_file_value(secret)
        app[OAUTH_TOKEN] = read_file_value(oauth)
        app.router.add_view('/slack/', cls)

    async def verify_request(self, body):
        headers = self.request.headers
        secret = self.request.app[VERIFICATION_SECRET]
        verify_signature(secret, headers, body)

    # Root request handlers

    async def process_unknown_request(self, body):
        _log.info(f'Unknown event type; body:\n{dump(body)}')
        raise web.HTTPOk

    async def process_challenge(self, body):
        return web.json_response({CHALLENGE: body[CHALLENGE]})

    async def process_event_callback(self, body):
        event = body[EVENT]
        event_handler = self._event_handlers.get(event[EVENT_TYPE], self.process_unknown_event)
        return await event_handler(body, event)

    # Event handlers

    async def process_base_message(self, body, event):
        _log.info('message received')
        subtype = event.get(EVENT_SUBTYPE)
        subhandler = self._message_subtype_handlers.get(
            subtype, self.process_unknown_message_subtype)
        return await subhandler(body, event)

    # Message handlers

    async def process_new_message(self, body, msg):
        if _log.getEffectiveLevel() <= logging.DEBUG:
            _log.debug(f'received new message:\n{json.dumps(msg, indent=4)}')
        codeblocks = get_codeblocks(msg[MSG_TEXT])
        if not codeblocks:
            raise web.HTTPOk

        executable_code = '\n\n'.join(codeblocks)
        session = get_session_name(msg)

        responder = partial(respond, self.request, msg)
        _log.info('executing embedded codeblocks')
        if _log.getEffectiveLevel() <= logging.DEBUG:
            _log.debug(f'executing code:\n{executable_code}')
        await self.execute(session, executable_code, responder)
        raise web.HTTPOk

    async def process_edited_message(self, body, msg):
        _log.info(f'received message:\n{dump(msg)}')
        raise web.HTTPOk

    async def process_unknown_message_subtype(self, body, msg):
        _log.info(f'unknown message subtype; message body:\n{dump(msg)}')
        raise web.HTTPOk

    async def process_unknown_event(self, body, event):
        _log.info(f'unknown event; event body:\n{event}')
        raise web.HTTPOk


def get_session_name(msg):
    return f"slack:{msg['channel_type']}:{msg['channel']}"


def dump(msg):
    return json.dumps(msg, indent=4)


def noop(*_, **__):
    raise web.HTTPOk


async def anoop(*_, **__):
    raise web.HTTPOk


def get_codeblocks(text):
    codeblocks = []

    blocks = [b.strip('\n') for b in text.split('```')]
    for i, block in enumerate(blocks):
        # Every other block is a codeblock starting with i==1.
        if i % 2:
            codeblocks.append(block)

    # If the last block was inside a codeblock, then it was a hanging
    # ``` and should be dropped
    if codeblocks and i % 2:
        codeblocks.pop()

    return codeblocks


def read_file_value(filename):
    with open(filename) as f:
        return f.read()
