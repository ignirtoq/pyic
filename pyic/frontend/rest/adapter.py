from asyncio import get_event_loop, CancelledError

from ...backend import SessionManager


SESSION_MANAGER = 'SessionManager'
SESSION_LISTENER = 'SessionResponseListener'
SESSION_RESPONSES = 'SessionResponses'


def attach_backend(app):
    sm = SessionManager()
    queue_map = {}

    app[SESSION_MANAGER] = sm
    app[SESSION_RESPONSES] = queue_map

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)


async def on_startup(app):
    sm = app[SESSION_MANAGER]
    queue_map = app[SESSION_RESPONSES]

    app[SESSION_LISTENER] = get_event_loop().create_task(
        listen(sm, queue_map))


async def on_shutdown(app):
    sm = app[SESSION_MANAGER]
    listener = app[SESSION_LISTENER]
    queue_map = app[SESSION_RESPONSES]

    # Stop all of the sessions.
    await sm.stop_all()
    # Stop the session listener if it's still running.
    if not listener.done():
        listener.cancel()
        await listener
    # Cancel any futures that haven't received responses.
    outstanding_futures = list(queue_map.values())
    for fut in outstanding_futures:
        fut.cancel()


async def listen(queue, queue_map):
    try:
        async for msg in queue:
            try:
                handler = _message_handlers[msg['msg_type']]
                get_event_loop().call_soon(handler, msg, queue_map)
            except KeyError:
                continue

    except CancelledError:
        pass


def _read_status(msg, queue_map):
    exec_state = msg.get('content', {}).get('executeion_state')
    if exec_state == 'idle':
        _stop_queue(msg, queue_map)


def _add_to_queue(msg, queue_map):
    msg_id = get_msg_id_from_msg(msg)
    queue = queue_map.get(msg_id)
    if queue is None:
        return
    queue.put_nowait(msg)


def _stop_queue(msg, queue_map):
    msg_id = get_msg_id_from_msg(msg)
    queue = queue_map.get(msg_id)
    if queue is None:
        return
    queue.stop_nowait()


_message_handlers = {
    'execute_result': _add_to_queue,
    'stream': _add_to_queue,
    'error': _add_to_queue,
    'statu': _read_status,
}


def get_msg_id_from_msg(msg):
    return msg['parent_header']['msg_id']
