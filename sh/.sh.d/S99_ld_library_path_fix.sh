# -----------------------------------------------------------------------------
# -- LD_LIBRARY_PATH Final Updates
# -----------------------------------------------------------------------------
# remove useless semicolons from LD_LIBRARY_PATH

if ! [[ "`uname`" == "Darwin" && "`uname -r`" == "12.1.0" ]]; then
    export LD_LIBRARY_PATH=$(echo $LD_LIBRARY_PATH | sed -e 's/:*$//g' -e 's/^:*//g')
fi;

