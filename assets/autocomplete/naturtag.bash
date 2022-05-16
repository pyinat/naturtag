# Autocomplete script for bash
# Re-generate with:
# _NATURTAG_COMPLETE=bash_source naturtag > assets/autocomplete/naturtag_complete.bash
# _NT_COMPLETE=bash_source nt >> assets/autocomplete/naturtag_complete.bash

_naturtag_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _NATURTAG_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

_naturtag_completion_setup() {
    complete -o nosort -F _naturtag_completion naturtag
}

_naturtag_completion_setup;

_nt_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _NT_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

_nt_completion_setup() {
    complete -o nosort -F _nt_completion nt
}

_nt_completion_setup;
