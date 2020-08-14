from functools import partial
import logging

from aiohttp import web

from .requests import SlackPythonSessions


def main(*, port, **cmdargs):
    app = SlackPythonSessions.get_app()
    SlackPythonSessions.add_app_routes(app, **cmdargs)

    web.run_app(app, port=port)


def setup_logging(verbosity):
    level = logging.ERROR - 10*verbosity
    logging.basicConfig(level=level)


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    p = argparse.ArgumentParser(__package__, add_help=False)
    p.add_argument('--help', action='help', help='show this message and exit')
    p.add_argument('-h', '--host', default='0.0.0.0', help='address to bind to')
    p.add_argument('-p', '--port', help='port to listen on', default=8080,
                   type=int)
    p.add_argument('-s', '--secret',
                   default=Path.home().joinpath('.slack/signing_secret'),
                   help='file containing Slack message verification secret')
    p.add_argument('-o', '--oauth',
                   default=Path.home().joinpath('.slack/oauth_token'),
                   help='file containing Slack oauth token for posting')
    p.add_argument('-v', action='count', default=0, help='verbose mode (can specify '
                                                         'multiple times)')
    cmdargs = vars(p.parse_args())

    setup_logging(cmdargs.pop('v'))
    main(**cmdargs)
