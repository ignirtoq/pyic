from pathlib import Path
import re
from setuptools import setup, find_packages


def find_version(*file_paths):
    version_file = Path(__file__).parent.joinpath(*file_paths).read_text()
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        version_file,
        re.M,
    )
    if version_match:
        return version_match.group(1)

    raise RuntimeError('Unable to find version string.')


NAME = 'pyic'
VERSION = find_version(NAME, '__init__.py')
LICENSE = 'MIT'
DESCRIPTION = 'Python In Chat'
LONG_DESCRIPTION = Path(__file__).parent.joinpath('README.md').read_text()
AUTHOR = 'Jeffrey Bouas'
EMAIL = 'ignirtoq+pyic@gmail.com'
PACKAGES = find_packages()
INSTALL_REQUIRES = [
    'aiohttp',
    'jupyter_client ~= 6.1',
]
TEST_SUITE = 'nose.collector'
TESTS_REQUIRE = ['pytest-asyncio']
CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
]
PYTHON_REQUIRES = '>=3.6'


setup(
    name=NAME,
    author=AUTHOR,
    author_email=EMAIL,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    version=VERSION,
    license=LICENSE,
    packages=PACKAGES,
    install_requires=INSTALL_REQUIRES,
    classifiers=CLASSIFIERS,
    test_suite=TEST_SUITE,
    tests_require=TESTS_REQUIRE,
    python_requires=PYTHON_REQUIRES,
)
