"""Combined CLI + GUI entry point"""
import sys

# CLI subcommands defined in naturtag/cli.py
_CLI_SUBCOMMANDS = {'tag', 'refresh', 'setup'}


def main():
    """Dispatch to CLI or GUI based on sys.argv.

    If any non-flag argument matches a known CLI subcommand, invoke the CLI.
    If --help or -h is present without a subcommand, show CLI help.
    Otherwise, launch the GUI.
    """
    args = sys.argv[1:]
    # Check if any non-flag argument matches a known CLI subcommand
    has_cli_subcommand = any(a in _CLI_SUBCOMMANDS for a in args if not a.startswith('-'))
    # Check for help flags
    has_help_flag = any(a in ('--help', '-h') for a in args)

    if has_cli_subcommand or has_help_flag:
        from naturtag.cli import main as cli_main
        cli_main(standalone_mode=True)
    else:
        from naturtag.app.app import main as gui_main
        gui_main()


if __name__ == '__main__':
    main()
