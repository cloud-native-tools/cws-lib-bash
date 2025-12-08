#!/bin/bash

# Source the environment
source $(dirname $0)/../bin/cws_bash_env

function test_func_2() {
    die "Something went wrong in func 2"
}

function test_func_1() {
    test_func_2
}

log info "Starting die test..."
test_func_1
log info "This should not be reached"
