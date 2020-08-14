from asyncio import get_event_loop, CancelledError

from ...backend import SessionManager


SESSION_MANAGER = 'SessionManager'
SESSION_LISTENER = 'SessionResponseListener'
SESSION_RESPONSES = 'SessionResponses'


def attach_backend(app):
    sm = SessionManager()
    future_map = {}

    app[SESSION_MANAGER] = sm
    app[SESSION_RESPONSES] = future_map

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)


async def on_startup(app):
    sm = app[SESSION_MANAGER]
    future_map = app[SESSION_RESPONSES]

    app[SESSION_LISTENER] = get_event_loop().create_task(
        listen(sm, future_map))


async def on_shutdown(app):
    sm = app[SESSION_MANAGER]
    listener = app[SESSION_LISTENER]
    future_map = app[SESSION_RESPONSES]

    # Stop all of the sessions.
    await sm.stop_all()
    # Stop the session listener if it's still running.
    if not listener.done():
        listener.cancel()
        await listener
    # Cancel any futures that haven't received responses.
    outstanding_futures = list(future_map.values())
    for fut in outstanding_futures:
        fut.cancel()


async def listen(queue, future_map):
    try:
        async for msg in queue:
            try:
                handler = _message_handlers[msg['msg_type']]
                get_event_loop().call_soon(handler, msg, future_map)
            except KeyError:
                continue

    except CancelledError:
        pass


def _forward_msg(msg, future_map):
    _set_future(msg, future_map, msg)


def _read_status(msg, future_map):
    exec_state = msg.get('content', {}).get('executeion_state')
    if exec_state == 'idle':
        _set_future(msg, future_map, None)


def _set_future(msg, future_map, value):
    msg_id = get_msg_id_from_msg(msg)
    future = future_map.get(msg_id)
    if future is None:
        return
    future.set_result(value)
    future_map.pop(msg_id)


_message_handlers = {
    'execute_result': _forward_msg,
    'stream': _forward_msg,
    'error': _forward_msg,
    'statu': _read_status,
}


def get_msg_id_from_msg(msg):
    return msg['parent_header']['msg_id']
