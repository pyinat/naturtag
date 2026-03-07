"""Copied/modified from https://github.com/click-contrib/click-help-colors

MIT License

Copyright (c) 2016 Roman Tonkonozhko

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import re
from typing import Any, Callable, Mapping, Sequence, TypeVar, overload

import click
from click.termui import _ansi_colors, _ansi_reset_all

CommandType = TypeVar('CommandType', bound=click.Command)
GroupType = TypeVar('GroupType', bound=click.Group)


class HelpColorsFormatter(click.HelpFormatter):
    options_regex = re.compile(r'-{1,2}[\w\-]+')

    def __init__(
        self,
        headers_color: str | None = None,
        options_color: str | None = None,
        options_custom_colors: Mapping[str, str] | None = None,
        indent_increment: int = 2,
        width: int | None = None,
        max_width: int | None = None,
    ):
        self.headers_color = headers_color
        self.options_color = options_color
        self.options_custom_colors = options_custom_colors
        super().__init__(indent_increment, width, max_width)

    def _get_opt_names(self, option_name: str) -> list[str]:
        opts = self.options_regex.findall(option_name)
        if not opts:
            return [option_name]
        else:
            # Include this for backwards compatibility
            opts.append(option_name.split()[0])
            return opts

    def _pick_color(self, option_name: str) -> str | None:
        opts = self._get_opt_names(option_name)
        for opt in opts:
            if self.options_custom_colors and (opt in self.options_custom_colors.keys()):
                return self.options_custom_colors[opt]
        return self.options_color

    def write_usage(self, prog: str, args: str = '', prefix: str | None = None) -> None:
        if prefix is None:
            prefix = 'Usage'

        colorized_prefix = _colorize(prefix, color=self.headers_color, suffix=': ')
        super().write_usage(prog, args, prefix=colorized_prefix)

    def write_heading(self, heading: str) -> None:
        colorized_heading = _colorize(heading, color=self.headers_color)
        super().write_heading(colorized_heading)

    def write_dl(
        self, rows: Sequence[tuple[str, str]], col_max: int = 30, col_spacing: int = 2
    ) -> None:
        colorized_rows = [(_colorize(row[0], self._pick_color(row[0])), row[1]) for row in rows]
        super().write_dl(colorized_rows, col_max, col_spacing)


class HelpColorsMixin:
    def __init__(
        self,
        help_headers_color: str | None = None,
        help_options_color: str | None = None,
        help_options_custom_colors: Mapping[str, str] | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        self.help_headers_color = help_headers_color
        self.help_options_color = help_options_color
        self.help_options_custom_colors = help_options_custom_colors
        super().__init__(*args, **kwargs)

    def get_help(self, ctx: click.Context) -> str:
        formatter = HelpColorsFormatter(
            width=ctx.terminal_width,
            max_width=ctx.max_content_width,
            headers_color=self.help_headers_color,
            options_color=self.help_options_color,
            options_custom_colors=self.help_options_custom_colors,
        )
        self.format_help(ctx, formatter)
        return formatter.getvalue().rstrip('\n')

    format_help: Callable[[click.Context, click.HelpFormatter], None]


class HelpColorsGroup(HelpColorsMixin, click.Group):
    @overload
    def command(self, __func: Callable[..., Any]) -> 'HelpColorsCommand': ...

    @overload
    def command(
        self,
        name: str | None,
        cls: type[CommandType],
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], CommandType]: ...

    @overload
    def command(
        self,
        name: None = ...,
        *,
        cls: type[CommandType],
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], CommandType]: ...

    @overload
    def command(
        self,
        name: str | None = ...,
        cls: None = ...,
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], 'HelpColorsCommand']: ...

    def command(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], CommandType] | 'HelpColorsCommand':
        kwargs.setdefault('cls', HelpColorsCommand)
        kwargs.setdefault('help_headers_color', self.help_headers_color)
        kwargs.setdefault('help_options_color', self.help_options_color)
        kwargs.setdefault('help_options_custom_colors', self.help_options_custom_colors)
        return super().command(*args, **kwargs)  # type: ignore

    @overload
    def group(self, __func: Callable[..., Any]) -> 'HelpColorsGroup': ...

    @overload
    def group(
        self,
        name: str | None,
        cls: type[GroupType],
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], GroupType]: ...

    @overload
    def group(
        self,
        name: None = ...,
        *,
        cls: type[GroupType],
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], GroupType]: ...

    @overload
    def group(
        self,
        name: str | None = ...,
        cls: None = ...,
        **attrs: Any,
    ) -> Callable[[Callable[..., Any]], 'HelpColorsGroup']: ...

    def group(
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], GroupType] | 'HelpColorsGroup':
        kwargs.setdefault('cls', HelpColorsGroup)
        kwargs.setdefault('help_headers_color', self.help_headers_color)
        kwargs.setdefault('help_options_color', self.help_options_color)
        kwargs.setdefault('help_options_custom_colors', self.help_options_custom_colors)
        return super().group(*args, **kwargs)  # type: ignore


class HelpColorsCommand(HelpColorsMixin, click.Command):
    pass


def _colorize(text: str, color: str | None = None, suffix: str | None = None) -> str:
    if not color or os.getenv('NO_COLOR'):
        return text + (suffix or '')
    try:
        return '\033[%dm' % (_ansi_colors[color]) + text + _ansi_reset_all + (suffix or '')
    except KeyError as err:
        raise KeyError(f'Unknown color {color!r}') from err
