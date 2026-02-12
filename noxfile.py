"""Notes:
* 'test' command: nox will use uv.lock to determine dependency versions
* 'lint' command: tools and environments are managed by pre-commit
* All other commands: the current environment will be used instead of creating new ones
"""

from os.path import join
from shutil import rmtree

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ['lint', 'cov']

CLEAN_DIRS = [
    'dist',
    'build',
    join('docs', '_build'),
    join('docs', 'modules'),
]
DEFAULT_COVERAGE_FORMATS = ['html', 'term']
DOC_BUILD_DIR = join('docs', '_build', 'html')
# Run tests in parallel, grouped by test module
XDIST_ARGS = ['--numprocesses=auto', '--dist=loadfile']


@nox.session(python=['3.14', '3.13'])
def test(session):
    """Run tests for a specific python version"""
    test_paths = session.posargs or ['test']
    session.run('uv', 'sync', '--frozen', external=True)
    session.run('uv', 'run', 'pytest', *XDIST_ARGS, *test_paths, external=True)


@nox.session(python=False)
def clean(session):
    """Clean up temporary build + documentation files"""
    for dir in CLEAN_DIRS:
        print(f'Removing {dir}')
        rmtree(dir, ignore_errors=True)


@nox.session(python=False, name='cov')
def coverage(session):
    """Run tests and generate coverage report"""
    cmd = ['pytest', '--cov']

    # Add coverage formats
    cov_formats = session.posargs or DEFAULT_COVERAGE_FORMATS
    cmd += [f'--cov-report={f}' for f in cov_formats]
    session.run(*cmd, 'test', *XDIST_ARGS)


@nox.session(python=False)
def docs(session):
    """Build Sphinx documentation"""
    session.run('sphinx-build', 'docs', DOC_BUILD_DIR, '-j', 'auto')


@nox.session(python=False)
def lint(session):
    """Run linters and code formatters via pre-commit"""
    session.run('prek', 'run', '--all-files')
