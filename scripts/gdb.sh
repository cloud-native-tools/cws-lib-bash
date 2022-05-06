function gdb_disassemble() {
  gdb -batch -ex "disassemble/rs ${1}" ${2}
}

