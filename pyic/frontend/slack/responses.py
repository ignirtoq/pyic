import aiohttp
import json
import logging

from .constants import OAUTH_TOKEN


__all__ = ['respond']

_log = logging.getLogger(__name__)


POST_URL = 'https://slack.com/api/chat.postMessage'


async def respond(request, slack_msg, jupyter_msg):
    response = get_slack_channel_and_thread(slack_msg)
    thread, channel = response['channel'], response['thread_ts']
    _log.info(f'message in channel {channel} thread {thread} processing complete')
    if jupyter_msg is None:
        _log.info(f'no Python response for message in channel {channel} '
                  f'thread {thread}')
        return

    try:
        text = get_jupyter_text(jupyter_msg)
    except KeyError:
        _log.warning(f'unknown Python message type "{juptyer_msg["msg_type"]}"')
        return

    response['text'] = text

    await send_response(request.app, response)


def get_slack_channel_and_thread(msg):
    channel = msg['channel']
    thread_ts = msg.get('thread_ts', msg['ts'])
    return {'channel': channel, 'thread_ts': thread_ts}


def get_jupyter_text(msg):
    parser = _msg_parsers[msg['msg_type']]
    return parser(msg)


def get_text_from_result(msg):
    return msg['content']['data']['text/plain']


def get_text_from_stream(msg):
    return msg['content']['text'].rstrip('\n')


def get_text_from_error(msg):
    return '\n'.join(msg['content']['traceback'])


_msg_parsers = {
    'execute_result': get_text_from_result,
    'stream': get_text_from_stream,
    'error': get_text_from_error,
}


async def send_response(app, body):
    token = app[OAUTH_TOKEN]
    headers = {
        'Content-type': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    data = json.dumps(body).encode()
    _log.info('sending Slack response message to Slack servers')
    async with aiohttp.ClientSession() as session:
        async with session.post(POST_URL, headers=headers, data=data) as r:
            if _log.getEffectiveLevel() <= logging.DEBUG:
                _log.debug(f'code response sent to Slack server; '
                           f'server response:\n{r}')
