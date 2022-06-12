function plantuml_mindmap2dir() {
    awk -f- $@ <<'EOF'
$1 ~/\*\*+/ {
    level=length($1);
    gsub(/ *\*+ +/,"",$0);
    l[level]=$0;
    if(level>2){
        printf "'"
        for(e in l){
            if (e<=level){
                printf l[e]"/"
            }
        };
        print "'"
    }
}
EOF
}
