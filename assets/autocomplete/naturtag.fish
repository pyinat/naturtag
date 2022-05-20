# Autocomplete script for fish shell
# Re-generate with:
# _NATURTAG_COMPLETE=fish_source naturtag > assets/autocomplete/naturtag.fish

function _naturtag_completion;
    set -l response;

    for value in (env _NATURTAG_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) naturtag);
        set response $response $value;
    end;

    for completion in $response;
        set -l metadata (string split "," $completion);

        if test $metadata[1] = "dir";
            __fish_complete_directories $metadata[2];
        else if test $metadata[1] = "file";
            __fish_complete_path $metadata[2];
        else if test $metadata[1] = "plain";
            echo $metadata[2];
        end;
    end;
end;

complete --no-files --command naturtag --arguments "(_naturtag_completion)";

function _nt_completion;
    set -l response;

    for value in (env _NT_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) nt);
        set response $response $value;
    end;

    for completion in $response;
        set -l metadata (string split "," $completion);

        if test $metadata[1] = "dir";
            __fish_complete_directories $metadata[2];
        else if test $metadata[1] = "file";
            __fish_complete_path $metadata[2];
        else if test $metadata[1] = "plain";
            echo $metadata[2];
        end;
    end;
end;

complete --no-files --command nt --arguments "(_nt_completion)";
