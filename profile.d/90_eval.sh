if [ $# -gt 1 ]
then
    if typeset -f $1; then
        fn=$1
        shift
        ${fn} $@
    else 
        eval "echo $1"
    fi
fi
