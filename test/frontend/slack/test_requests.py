from pyslackapp.frontend.slack.requests import get_codeblocks


HAS_CODEBLOCK = """
hi
```
code
```"""
HAS_CODEBLOCK_EXPECTED = "code"

NO_CODEBLOCK = """
hi
"""

TWO_CODEBLOCKS = """```
first
```
not code
```
second
```"""
TWO_CODEBLOCKS_EXPECTED = ["first", "second"]

INCOMPLETE_CODEBLOCK = "```one```not```two```not```not"
INCOMPLETE_CODEBLOCK_EXPECTED = ["one", "two"]


def test_get_codeblocks_no_codeblock():
    assert not get_codeblocks(NO_CODEBLOCK)


def test_get_codeblocks_one_codeblock():
    cb = get_codeblocks(HAS_CODEBLOCK)
    assert len(cb) == 1
    assert cb[0] == HAS_CODEBLOCK_EXPECTED


def test_get_codeblocks_two_codeblocks():
    cb = get_codeblocks(TWO_CODEBLOCKS)
    assert cb == TWO_CODEBLOCKS_EXPECTED


def test_get_codeblocks_incomplete():
    cb = get_codeblocks(INCOMPLETE_CODEBLOCK)
    assert cb == INCOMPLETE_CODEBLOCK_EXPECTED
