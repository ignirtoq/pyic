# pyic: Python Interpreters for Chat
pyic is an MIT-licensed application for integrating Python interpreters into
your chat system of choice.

pyic puts a bot (pybot) in each desired channel that watches for code blocks.
When it sees one, it runs the code block in a Python interpreter and prints
the results as a reply to the thread (if supported), in the channel, or as
a response to a direct message.

## Features
* Isolated interpreters for each channel (or user for direct messages)
* Modular design, so adding new front-ends for new chat clients is simple.
* Supported chat systems:
    * Slack
