#!/usr/bin/env bash
# script-interface.sh — the bash half of the script-interface contract (feature 086).
#
# OWNER OF THE RULE: `.specify/shared/definitions/script-interface-definitions.md` (sections 3 and 4).
# This file is the executable form of that rule and owns nothing else; the Python half is
# `.specify/scripts/python/script_interface_cli.py`. It carries no rule table and no literal version:
# the version is re-derived at run time by the bounded upward search section 2 fixes.
#
# It is a LIBRARY. Sourcing it defines two functions and runs nothing; it writes nothing and
# prints nothing when sourced, and it has no entry point of its own.
#
# Usage:
#   -h, --help        answer this library's own surface: print this block, exit 0
#   --version         answer `<script-name> <framework-version>`, exit 0
#   define <label>... declare a consuming script's surface (see below)
#   guard "$@"        answer the flags and reject an unrecognized option, once defined
#
# side-effects: none. Sourcing, defining and answering write nothing and touch no path.
# exit-codes: 0 a flag was answered; 2 an unrecognized option; 3 no definition given.
#
# A consuming script puts these four steps ABOVE `source common.sh` and above every write:
#
#   SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   . "$SCRIPT_DIR/script-interface.sh"                       # no action
#   script_interface_guard entry                              # at FILE SCOPE, before any function
#   script_interface_guard define name="$0" effects="rebuilds memo.md" \
#       codes="0 ok; 2 unrecognized option" \
#       usage="[--json] [--force]" -- --json --force           # its own options, after `--`
#   script_interface_guard guard "$@"                        # answers, then returns
#
# The scan is a `case` loop over `"$@"`, never `getopts`: `getopts` stops at `--` and does not
# reject an unknown long option, so it cannot enforce section 4. The loop honours the bare `--`
# terminator itself. Each flag limb exits INSIDE the loop, so a flag wins over any action
# option riding with it, in either argument order. A recognized option never rescues an
# unrecognized one: every `-*` token before the terminator is judged on its own, against the
# declared set — so a legal option is never refused and an unknown one never reaches the main
# action.

_SCRIPT_INTERFACE_VERSION_SOURCE="pyproject.toml"
_SCRIPT_INTERFACE_MAX_LEVELS=12

# Resolution of a consuming script's declaration; every field is empty until `define` runs.
_SCRIPT_INTERFACE_NAME=""
_SCRIPT_INTERFACE_DIR=""
_SCRIPT_INTERFACE_USAGE=""
#: The declared option tokens, each surrounded by spaces on BOTH sides, so a substring test
#: a `*" $token "*` test is exact: without the leading space `-n` would match inside a
#: longer option's tail.
_SCRIPT_INTERFACE_OPTIONS="  "
_SCRIPT_INTERFACE_SIDE_EFFECTS=""
_SCRIPT_INTERFACE_EXIT_CODES=""
#: The options that trigger the script's main write, each space-padded like the option set.
#: C-11 reads this: the help path MUST win over the very option the script writes on.
_SCRIPT_INTERFACE_WRITES="  "
#: `1` when the consumer forwards its arguments onward, so an unknown `-*` token is an
#: OPERAND for the downstream parser rather than a flag of this script's own.
_SCRIPT_INTERFACE_PASS_THROUGH=""
#: `1` when the consumer is a LIBRARY command: a file whose direct-invocation entry point is
#: "publish the helper functions". Declared with the `library` word; the entry point itself is
#: `_script_interface_library_link` below, so a consumer writes no wrapper of its own.
#:
#: Why this distinction lives in the library and not in each script: a `main() { ... }` wrapper
#: is the right shape for a COMMAND, where running and sourcing are different acts, and exactly
#: the wrong shape for a LIBRARY, whose contract is that sourcing it yields its functions. The
#: shared library is the one place that already knows which consumers are which (C-5, one
#: owner); re-deriving it per file produced twelve commands that had stopped being the libraries
#: they are documented to be — measuring "last action position" found `main()`'s own definition
#: line, and the fix that answered it wrapped every file, library-shaped ones included.
_SCRIPT_INTERFACE_LIBRARY_CMD=""

#: The consumer's own `$0`, recorded by the `entry` call its file makes before anything reads it.
#: `$0` is reliable only in the scope that owns it: at a library's file scope it names the entry of
#: whatever shell the `source` ran in, and inside a function it names the sourced file instead.
_SCRIPT_INTERFACE_ENTRY="${_SCRIPT_INTERFACE_ENTRY:-}"

#: `0` while nothing has been read into this shell, `1` once a file has. Every applicable script
#: records itself (`entry`) and every file read into a shell records the same flag at its top, so
#: the two cannot disagree: a nested `common.sh` reached from a command's `main()` is then "read
#: in", not "the running program" (measured: without it each consumer declared `library` from
#: inside its own `main()` and every declared flag was rejected with the library's surface).
_SCRIPT_INTERFACE_READ_IN="${_SCRIPT_INTERFACE_READ_IN:-0}"

#: `1` when THIS FILE was read into the shell rather than run as the program. The comparison is
#: made once, at load, before any `$0` can be rewritten by a caller.
_SCRIPT_INTERFACE_SOURCED_INTO=""
case "${BASH_SOURCE[0]}" in
    /*) [ "${BASH_SOURCE[0]}" = "$0" ] || _SCRIPT_INTERFACE_SOURCED_INTO=1 ;;
    *) [ "${BASH_SOURCE[0]}" = "$0" ] || [ "${BASH_SOURCE[0]}" = "./$0" ] \
        || _SCRIPT_INTERFACE_SOURCED_INTO=1 ;;
esac

# Resolve `<script-name> <framework-version>` by the bounded upward search section 2 fixes:
# from the script's own directory to the nearest ancestor carrying BOTH `pyproject.toml` and a
# `.git` entry, never beyond it. No source found is the observation `unknown`, exit 0.
_script_interface_version() {
    local _dir _level _ver
    _dir="${1:-.}"
    case "$_dir" in /*) ;; *) _dir="./$_dir" ;; esac
    _ver="unknown"
    _level=0
    while [ -d "$_dir" ] && [ "$_level" -le "$_SCRIPT_INTERFACE_MAX_LEVELS" ]; do
        if [ -f "$_dir/$_SCRIPT_INTERFACE_VERSION_SOURCE" ] && [ -e "$_dir/.git" ]; then
            _ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' \
                "$_dir/$_SCRIPT_INTERFACE_VERSION_SOURCE" 2>/dev/null | head -n 1)"
            [ -n "$_ver" ] || _ver="unknown"
            break
        fi
        [ "$_dir" = "/" ] && break
        _dir="$(dirname -- "$_dir")"
        _level=$((_level + 1))
    done
    printf '%s\n' "$_ver"
}

# The `--version` LINE, as one function: `<script-name> <framework-version>`, and `unknown` when
# the bounded search finds no source (C-8: an observation, never a violation).
#
# This is the published helper, not an internal step of the guard. A consumer that cannot find
# this library at all -- a downstream copy without the `scripts` pair, a tree whose `common.sh`
# is broken -- still has to answer `--version`, and the guard block a projected mirror carries
# answers it by CALLING this function. The projection does not retype it: `sync-mirrors.py` fills
# its `__SCRIPT_INTERFACE_VERSION_BODY__` sentinel with the body below, so the two spellings of
# the search are one text (the sentinel is not written here; only the owner page and the engine
# name it).
#
#   script_interface_version_text <name> [dir]   # name as it should be printed, dir to search from
#
# Both arguments are optional: with no name the caller's own `$0` is used, and with no directory
# `$0`'s directory is. It prints exactly one line and returns 0 in every case, including the
# no-source one, so a caller may use it directly in output.
#
# Every constant it needs is DEFAULTED INSIDE the body rather than read from the file-scope
# variables above. That is what makes the body portable: the projection splices it into a file
# that never sources this library (a downstream `.specify/` copy), so it may not depend on a
# variable defined here. The two defaults repeat the file-scope values above because the spliced
# copy has no file scope to read them from; the contract suite asserts the pair stays equal.
script_interface_version_text() {
    local _name _dir _level _ver
    local _source="${_SCRIPT_INTERFACE_VERSION_SOURCE:-pyproject.toml}"
    local _max="${_SCRIPT_INTERFACE_MAX_LEVELS:-12}"
    # The printed name is the BASENAME of what the caller passed, exactly as the Python half
    # prints `Path(argv[0]).name`: a caller that forwards `$0` gets the same word the other
    # side of the tree writes, and a downstream copy's path never leaks into the line.
    _name="${1:-$0}"
    _name="${_name##*/}"
    _dir="${2:-$(dirname -- "$0")}"
    case "$_dir" in /*) ;; *) _dir="./$_dir" ;; esac
    _ver="unknown"
    _level=0
    while [ -d "$_dir" ] && [ "$_level" -le "$_max" ]; do
        if [ -f "$_dir/$_source" ] && [ -e "$_dir/.git" ]; then
            _ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' \
                "$_dir/$_source" 2>/dev/null | head -n 1)"
            break
        fi
        [ "$_dir" = "/" ] && break
        _dir="$(dirname -- "$_dir")"
        _level=$((_level + 1))
    done
    [ -n "$_ver" ] || _ver="unknown"
    printf '%s %s\n' "$_name" "$_ver"
    return 0
}

# The `-h` / `--help` body: the usage synopsis, the declared options, then the four labels the
# owner page fixes as a closed set. One body for both spellings.
_script_interface_usage() {
    local _name="${_SCRIPT_INTERFACE_NAME:-script-interface.sh}" _opt
    printf 'usage: %s %s\n' "$_name" "${_SCRIPT_INTERFACE_USAGE:-[options]}"
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    for _opt in $_SCRIPT_INTERFACE_OPTIONS; do
        case "$_opt" in -h|--help|--version) continue ;; esac
        # The C-11 option is marked in the body's own text: that is where the contract reads
        # "the write-triggering option" from, and a bare token there would be indistinguishable
        # from an ordinary flag.
        if [ "${_SCRIPT_INTERFACE_WRITES#*" $_opt "}" != "$_SCRIPT_INTERFACE_WRITES" ]; then
            printf '  %s (triggers the write)\n' "$_opt"
        else
            printf '  %s\n' "$_opt"
        fi
    done
    printf 'side-effects: %s\n' \
        "${_SCRIPT_INTERFACE_SIDE_EFFECTS:-none; the flags write nothing}"
    printf 'exit-codes: %s\n' \
        "${_SCRIPT_INTERFACE_EXIT_CODES:-0 the request was answered; 2 an unrecognized option}"
}

# The one function a consuming script calls, twice: once to declare, once to answer.
#
#   script_interface_guard entry               # file scope only; records the caller's entry
#   script_interface_guard define name=PATH [usage=TEXT] [effects=TEXT]
#                                [codes=TEXT] [writes=OPTION]... [passthrough] [library] -- OPTION...
#   script_interface_guard guard "$@"          # note: no extra `--`, it is the terminator
#
# `define` never exits and never prints: it only records the declaration. `guard` is one loop
# over its arguments; it exits 0 on `-h` / `--help` / `--version`, exits 2 on any `-*` token
# not in the declared set, and returns 0 to the caller when there is nothing to answer.
#
# The `$1` sub-command and the arguments after it are shifted apart BEFORE any loop runs: a
# single `for` over `"$@"` would meet the leading `guard` word, and a literal `--` written at
# the call site would be swallowed as the caller's terminator instead of reaching the scan.
script_interface_guard() {
    local _mode _rec _stop=0
    _mode="${1:-}"
    case "$_mode" in
        define|guard|entry) [ "$#" -gt 0 ] && shift ;;
    esac
    case "$_mode" in
        define)
            _SCRIPT_INTERFACE_NAME=""
            _SCRIPT_INTERFACE_DIR=""
            _SCRIPT_INTERFACE_USAGE=""
            _SCRIPT_INTERFACE_OPTIONS="  "
            _SCRIPT_INTERFACE_SIDE_EFFECTS=""
            _SCRIPT_INTERFACE_EXIT_CODES=""
            _SCRIPT_INTERFACE_WRITES="  "
            _SCRIPT_INTERFACE_PASS_THROUGH=""
            _SCRIPT_INTERFACE_LIBRARY_CMD=""
            for _rec in "$@"; do
                if [ "$_stop" -eq 1 ]; then
                    _SCRIPT_INTERFACE_OPTIONS="$_SCRIPT_INTERFACE_OPTIONS $_rec "
                    continue
                fi
                # The declaration words are `key=value` LABELS, never `--flag` spellings:
                # a `--side-effects=` token in the source would itself look like an option to
                # a reader (and to any scanner reading the script's own text) and would sit in
                # the very place the contract's write-option probe reads.
                case "$_rec" in
                    --) _stop=1 ;;
                    name=*)
                        _SCRIPT_INTERFACE_DIR="$(dirname -- "${_rec#name=}")"
                        _SCRIPT_INTERFACE_NAME="${_rec#name=}"
                        _SCRIPT_INTERFACE_NAME="${_SCRIPT_INTERFACE_NAME##*/}"
                        ;;
                    usage=*) _SCRIPT_INTERFACE_USAGE="${_rec#usage=}" ;;
                    effects=*) _SCRIPT_INTERFACE_SIDE_EFFECTS="${_rec#effects=}" ;;
                    codes=*) _SCRIPT_INTERFACE_EXIT_CODES="${_rec#codes=}" ;;
                    writes=*) _SCRIPT_INTERFACE_WRITES="$_SCRIPT_INTERFACE_WRITES ${_rec#writes=} " ;;
                    passthrough) _SCRIPT_INTERFACE_PASS_THROUGH=1 ;;
                    library) _SCRIPT_INTERFACE_LIBRARY_CMD=1 ;;
                    *)
                        printf 'error: define: unrecognized declaration: %s\n' "$_rec" >&2
                        return 3
                        ;;
                esac
            done
            [ -n "$_SCRIPT_INTERFACE_NAME" ] && return 0
            printf 'error: define: name=PATH is required\n' >&2
            return 3
            ;;
        guard)
            # `_stop` is a `local` of THIS function, so it survives from the `define` call
            # above; it is reset here or the scan below would start already terminated.
            _stop=0
            [ -n "$_SCRIPT_INTERFACE_NAME" ] || return 0
            # C-9 / C-11, in one pass: judge EVERY token before answering ANY flag, so a
            # recognized option never rescues an unrecognized one (`--help --bogus` is red),
            # and remember the first flag seen so the answer happens after the whole line is
            # known. The answer still precedes the caller's main action: `guard` exits here.
            local _wanted=""
            for _rec in "$@"; do
                [ "$_stop" -eq 1 ] && continue
                case "$_rec" in
                    --) _stop=1 ;;
                    -h|--help) [ -n "$_wanted" ] || _wanted="help" ;;
                    --version) [ -n "$_wanted" ] || _wanted="version" ;;
                    -*)
                        # A declared option is one of the tokens `define` recorded, each
                        # stored space-padded on both sides. The test is `if`, not an outer
                        # `case` arm: a quoted variable inside a `case` PATTERN is not a
                        # reliable expansion, and a silently-unmatched arm here would reject
                        # every legal option (measured while landing T059).
                        if [ "${_SCRIPT_INTERFACE_OPTIONS#*" $_rec "}" \
                            != "$_SCRIPT_INTERFACE_OPTIONS" ]; then
                            :                                        # a declared option
                        elif [ -n "$_SCRIPT_INTERFACE_PASS_THROUGH" ]; then
                            # A pass-through consumer forwards its line to another parser, so
                            # an undeclared token belongs to THAT parser; rejecting it here
                            # would change the existing interface (FR-018).
                            :
                        else
                            printf 'error: unrecognized option: %s\n' "$_rec" >&2
                            _script_interface_usage >&2
                            exit 2
                        fi
                        ;;
                esac
            done
            case "$_wanted" in
                help) _script_interface_usage; exit 0 ;;
                version)
                    printf '%s %s\n' "$_SCRIPT_INTERFACE_NAME" \
                        "$(_script_interface_version "${_SCRIPT_INTERFACE_DIR:-.}")"
                    exit 0
                    ;;
            esac
            return 0
            ;;
        entry)
            # Record the consumer's own `$0`, in the consumer's own scope: ONE word, no scan, so a
            # `set -e` caller cannot have the capture mistaken for a failing test. It must run at
            # FILE SCOPE of the consumer (see the usage block above): inside `main()` a local of
            # the same name would shadow it, and an unset local is just "empty".
            # An ENTRY is a file nobody read in: its `$0` is the text the shell was handed, so it
            # is recorded only when the entry above is still empty. A file READ INTO a shell
            # (`common.sh` reached from a command's `main()`) must not overwrite the running
            # program's entry, or the consumer's own guard would answer with the child's `$0` —
            # measured as every declared flag of every command rejected by `common.sh`'s surface.
            # An ENTRY is a file nobody read in: its `$0` is the text the shell was handed, so it
            # is recorded only when the entry above is still empty. A file READ INTO a shell
            # (`common.sh` reached from a command's `main()`) must not overwrite the running
            # program's entry, or the consumer's own guard would answer with the child's `$0`.
            [ -n "$_SCRIPT_INTERFACE_ENTRY" ] || _SCRIPT_INTERFACE_ENTRY="$0"
            _SCRIPT_INTERFACE_READ_IN=1
            # `library` belongs to the file that is running, and `entry` marks that file: drop it
            # here or a nested host would keep answering its parent's flags with its own surface.
            _SCRIPT_INTERFACE_LIBRARY_CMD=""
            # A declaration belongs to the file that is running, and the last file to declare is
            # that one: entering a consumer releases whatever a library had declared before it.
            _SCRIPT_INTERFACE_LIBRARY_CMD=""
            return 0
            ;;
        -h|--help)
            sed -n '2,40p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//' || :
            return 0
            ;;
        --version)
            printf '%s %s\n' "${0##*/}" "$(_script_interface_version "$(dirname -- "$0")")"
            exit 0
            ;;
        *)
            printf 'usage: script_interface_guard define|guard ...\n' >&2
            return 2
            ;;
    esac
}

# The sourceable half of a library command's entry point. A library command lists the helper
# names it publishes, defines nothing at file scope except `_script_interface_library_body`, and
# calls `_script_interface_library_link` as its last statement. Sourcing such a file yields the
# listed helpers; running it runs the body. That is the whole difference between a library and a
# command, and it is decided HERE, once, because it is the only place that knows both.
#
# Why a subshell: a library that runs a dependency check at its top level (`exit 1` when the host
# environment is absent) ends whatever shell sources it. Running the body in a subshell and
# re-defining what it produced in the caller turns that from "kills the caller" into a result the
# caller can act on: the helpers produced before a failure are still the caller's, and the
# caller's own shell survives.
#
# Why an explicit list rather than the subshell's whole function table: the body sources the
# host's shell library, whose table carries environment-bound functions of its own. Publishing
# those would hand a caller functions that were never this file's to give. The list IS the
# declaration of what this file publishes; nothing else crosses the subshell boundary.
#
# No `local` in these three: `local` is meaningless at file scope, where a library's body and
# this call both sit.
_script_interface_library_link() {
    if [ "${BASH_SOURCE[0]}" = "${_SCRIPT_INTERFACE_ENTRY:-$0}" ]; then
        _script_interface_library_body
        return $?
    fi
    _script_interface_library_import "$(_script_interface_library_capture "$@")" "$@"
    return 0
}

# Run the body in a subshell and print ONE definition per published name. This is the one place a
# library command's body is executed while the file is being sourced.
_script_interface_library_capture() {
    local _name
    (
        _script_interface_library_body
        for _name in "$@"; do
            declare -f "$_name"
        done
    )
}

# Define the captured helpers in the CALLER's shell. The capture is the body's own output, in the
# caller's own dialect, produced by the caller's own shell: the `eval` below therefore evaluates
# definitions and nothing else. A name the body never defined is skipped, not reported — the
# caller's contract is "the helpers you listed are mine now".
_script_interface_library_import() {
    local _capture="$1" _name _block _line _inside
    shift
    for _name in "$@"; do
        case "$_capture" in
            *"$_name () "*) : ;;
            *) continue ;;
        esac
        _block=""
        _inside=0
        while IFS= read -r _line; do
            if [ "$_inside" -eq 0 ]; then
                case "$_line" in
                    "$_name () "*) _inside=1 ;;
                esac
            fi
            [ "$_inside" -eq 1 ] || continue
            _block="$_block$_line"$'\n'
            if [ "$_line" = "}" ]; then
                break
            fi
        done <<LIBRARY_CAPTURE
$_capture
LIBRARY_CAPTURE
        eval "$_block"
    done
}

# Self-application (the library obeys the contract it ships). Guarded on the SOURCED flag this
# file set at its own top, so sourcing it still defines the functions above and runs nothing.
#
# Why not `[ "${BASH_SOURCE[0]}" = "$0" ]` here: a `source` of this file inside a consumer that is
# ITSELF being sourced (`common.sh` is sourced into a command, and that command sources this file)
# carries `$0` = the command and `BASH_SOURCE[0]` = this library's path, so the comparison says
# "not the entry" for the one case that IS the entry — measured as a consumer answering its own
# declared flags with this library's surface. `$0` is deliberately left untouched: the consumer's
# own `guard` call captures it (see `_SCRIPT_INTERFACE_ENTRY`) and its own body still reads it.
if [ "${_SCRIPT_INTERFACE_SOURCED_INTO:-}" != "1" ] && [ "$_SCRIPT_INTERFACE_READ_IN" = "0" ]; then
    script_interface_guard define name="$0" \
        usage="define|guard ...; as a library it is sourced, not run" \
        effects="none; the library and its flags change nothing" \
        codes="0 the flag was answered; 2 an unrecognized option; 3 a malformed declaration" \
        writes=--help \
        --
    script_interface_guard guard "$@"
fi
