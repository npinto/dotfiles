if [[ "`uname`" == "Darwin" ]]; then
    if [[ "`uname -r`" == "10.8.0" ]]; then
        export DYLD_LIBRARY_PATH=$LD_LIBRARY_PATH
    fi;
    #if [[ "`uname -r`" == "12.1.0" ]]; then
    #fi;
fi;
