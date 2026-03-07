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
import typing as t

import click
from click import Command
from click import version_option as click_version_option
from click.termui import _ansi_colors, _ansi_reset_all

CommandType = t.TypeVar('CommandType', bound=click.Command)
GroupType = t.TypeVar('GroupType', bound=click.Group)
FC = t.TypeVar('FC', bound=t.Union[t.Callable[..., t.Any], Command])


class HelpColorsFormatter(click.HelpFormatter):
    options_regex = re.compile(r'-{1,2}[\w\-]+')

    def __init__(
        self,
        headers_color: t.Optional[str] = None,
        options_color: t.Optional[str] = None,
        options_custom_colors: t.Optional[t.Mapping[str, str]] = None,
        indent_increment: int = 2,
        width: t.Optional[int] = None,
        max_width: t.Optional[int] = None,
    ):
        self.headers_color = headers_color
        self.options_color = options_color
        self.options_custom_colors = options_custom_colors
        super().__init__(indent_increment, width, max_width)

    def _get_opt_names(self, option_name: str) -> t.List[str]:
        opts = self.options_regex.findall(option_name)
        if not opts:
            return [option_name]
        else:
            # Include this for backwards compatibility
            opts.append(option_name.split()[0])
            return opts

    def _pick_color(self, option_name: str) -> t.Optional[str]:
        opts = self._get_opt_names(option_name)
        for opt in opts:
            if self.options_custom_colors and (opt in self.options_custom_colors.keys()):
                return self.options_custom_colors[opt]
        return self.options_color

    def write_usage(self, prog: str, args: str = '', prefix: t.Optional[str] = None) -> None:
        if prefix is None:
            prefix = 'Usage'

        colorized_prefix = _colorize(prefix, color=self.headers_color, suffix=': ')
        super().write_usage(prog, args, prefix=colorized_prefix)

    def write_heading(self, heading: str) -> None:
        colorized_heading = _colorize(heading, color=self.headers_color)
        super().write_heading(colorized_heading)

    def write_dl(
        self, rows: t.Sequence[t.Tuple[str, str]], col_max: int = 30, col_spacing: int = 2
    ) -> None:
        colorized_rows = [(_colorize(row[0], self._pick_color(row[0])), row[1]) for row in rows]
        super().write_dl(colorized_rows, col_max, col_spacing)


class HelpColorsMixin:
    def __init__(
        self,
        help_headers_color: t.Optional[str] = None,
        help_options_color: t.Optional[str] = None,
        help_options_custom_colors: t.Optional[t.Mapping[str, str]] = None,
        *args: t.Any,
        **kwargs: t.Any,
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

    format_help: t.Callable[[click.Context, click.HelpFormatter], None]


class HelpColorsGroup(HelpColorsMixin, click.Group):
    @t.overload
    def command(self, __func: t.Callable[..., t.Any]) -> 'HelpColorsCommand': ...

    @t.overload
    def command(
        self,
        name: t.Optional[str],
        cls: t.Type[CommandType],
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], CommandType]: ...

    @t.overload
    def command(
        self,
        name: None = ...,
        *,
        cls: t.Type[CommandType],
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], CommandType]: ...

    @t.overload
    def command(
        self,
        name: t.Optional[str] = ...,
        cls: None = ...,
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], 'HelpColorsCommand']: ...

    def command(
        self,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> t.Union[t.Callable[[t.Callable[..., t.Any]], CommandType], 'HelpColorsCommand']:
        kwargs.setdefault('cls', HelpColorsCommand)
        kwargs.setdefault('help_headers_color', self.help_headers_color)
        kwargs.setdefault('help_options_color', self.help_options_color)
        kwargs.setdefault('help_options_custom_colors', self.help_options_custom_colors)
        return super().command(*args, **kwargs)  # type: ignore

    @t.overload
    def group(self, __func: t.Callable[..., t.Any]) -> 'HelpColorsGroup': ...

    @t.overload
    def group(
        self,
        name: t.Optional[str],
        cls: t.Type[GroupType],
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], GroupType]: ...

    @t.overload
    def group(
        self,
        name: None = ...,
        *,
        cls: t.Type[GroupType],
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], GroupType]: ...

    @t.overload
    def group(
        self,
        name: t.Optional[str] = ...,
        cls: None = ...,
        **attrs: t.Any,
    ) -> t.Callable[[t.Callable[..., t.Any]], 'HelpColorsGroup']: ...

    def group(
        self, *args: t.Any, **kwargs: t.Any
    ) -> t.Union[t.Callable[[t.Callable[..., t.Any]], GroupType], 'HelpColorsGroup']:
        kwargs.setdefault('cls', HelpColorsGroup)
        kwargs.setdefault('help_headers_color', self.help_headers_color)
        kwargs.setdefault('help_options_color', self.help_options_color)
        kwargs.setdefault('help_options_custom_colors', self.help_options_custom_colors)
        return super().group(*args, **kwargs)  # type: ignore


class HelpColorsCommand(HelpColorsMixin, click.Command):
    pass


class HelpColorsMultiCommand(HelpColorsMixin, click.MultiCommand):
    def resolve_command(
        self,
        ctx: click.Context,
        args: t.List[str],
    ) -> t.Tuple[t.Optional[str], t.Optional[click.Command], t.List[str]]:
        cmd_name, cmd, args[1:] = super().resolve_command(ctx, args)

        if cmd is not None:
            if not isinstance(cmd, HelpColorsMixin):
                if isinstance(cmd, click.Group):
                    _extend_instance(cmd, HelpColorsGroup)
                    cmd = t.cast(HelpColorsGroup, cmd)
                if isinstance(cmd, click.Command):
                    _extend_instance(cmd, HelpColorsCommand)
                    cmd = t.cast(HelpColorsCommand, cmd)

            if not getattr(cmd, 'help_headers_color', None):
                cmd.help_headers_color = self.help_headers_color
            if not getattr(cmd, 'help_options_color', None):
                cmd.help_options_color = self.help_options_color
            if not getattr(cmd, 'help_options_custom_colors', None):
                cmd.help_options_custom_colors = self.help_options_custom_colors

        return cmd_name, cmd, args[1:]


@t.overload
def version_option(
    version: str,
    prog_name: str,
    message: None = ...,
    message_color: t.Optional[str] = ...,
    prog_name_color: t.Optional[str] = ...,
    version_color: t.Optional[str] = ...,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]: ...


@t.overload
def version_option(
    version: t.Optional[str] = ...,
    prog_name: t.Optional[str] = ...,
    message: str = ...,
    message_color: t.Optional[str] = ...,
    prog_name_color: t.Optional[str] = ...,
    version_color: t.Optional[str] = ...,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]: ...


def version_option(
    version: t.Optional[str] = None,
    prog_name: t.Optional[str] = None,
    message: t.Optional[str] = None,
    message_color: t.Optional[str] = None,
    prog_name_color: t.Optional[str] = None,
    version_color: t.Optional[str] = None,
    **kwargs: t.Any,
) -> t.Callable[[FC], FC]:
    """
    :param prog_name_color: color of the prog_name.
    :param version_color: color of the version.
    :param message_color: default color of the message.

    for other params see Click's version_option decorator:
    https://click.palletsprojects.com/en/7.x/api/#click.version_option
    """
    if message is None:
        message = '%(prog)s, version %(version)s'

    msg_parts = []
    for s in re.split(r'(%\(version\)s|%\(prog\)s)', message):
        if s == '%(prog)s':
            if prog_name is None:
                raise TypeError("version_option() missing required argument: 'prog_name'")
            msg_parts.append(_colorize(prog_name, prog_name_color or message_color))
        elif s == '%(version)s':
            if version is None:
                raise TypeError("version_option() missing required argument: 'version'")
            msg_parts.append(_colorize(version, version_color or message_color))
        else:
            msg_parts.append(_colorize(s, message_color))
    message = ''.join(msg_parts)

    return click_version_option(version=version, prog_name=prog_name, message=message, **kwargs)


class HelpColorsException(Exception):
    pass


def _colorize(text: str, color: t.Optional[str] = None, suffix: t.Optional[str] = None) -> str:
    if not color or os.getenv('NO_COLOR'):
        return text + (suffix or '')
    try:
        return '\033[%dm' % (_ansi_colors[color]) + text + _ansi_reset_all + (suffix or '')
    except KeyError:
        raise HelpColorsException('Unknown color %r' % color)


def _extend_instance(obj: object, cls: t.Type[object]) -> None:
    """Apply mixin to a class instance after creation"""
    base_cls = obj.__class__
    base_cls_name = obj.__class__.__name__
    obj.__class__ = type(base_cls_name, (cls, base_cls), {})
