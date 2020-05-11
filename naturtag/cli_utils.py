from glob import glob
from itertools import chain
from os.path import expanduser
from re import compile, DOTALL, MULTILINE

import click

CODE_BLOCK = compile(r'```\n(.+?)```\s*\n', DOTALL)
CODE_INLINE = compile(r'`([^`]+?)`')
HEADER = compile(r'^\#+\s*(.*)$', MULTILINE)


class GlobPath(click.Path):
    """ A parameter type that expands glob patterns """
    def convert(self, value, param, ctx):
        matches = [expanduser(m) for m in glob(value)]
        return [click.Path.convert(self, m, param, ctx) for m in matches]


def chain_lists(ctx, param, value):
    return list(chain.from_iterable(value))


def colorize_help_text(text):
    """ An ugly hack to make help text prettier """
    text = HEADER.sub(click.style(r'\1:', 'blue'), text)
    text = CODE_BLOCK.sub(click.style(r'\1', 'cyan'), text)
    text = CODE_INLINE.sub(click.style(r'\1', 'cyan'), text)
    return text


def strip_url(ctx, param, value):
    """ If a URL is provided containing an ID, return just the ID """
    return int(value.split('/')[-1].split('-')[0]) if value else None
