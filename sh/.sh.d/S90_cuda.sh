# -----------------------------------------------------------------------------
# -- CUDA related
# -----------------------------------------------------------------------------

if ! [[ "`uname`" == "Darwin" && "`uname -r`" == "12.1.0" ]]; then
    test -d /usr/local/cuda/bin && export PATH=$PATH:/usr/local/cuda/bin;
    test -d /usr/local/cuda/lib && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib;
    test -d /usr/local/cuda/lib64 && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64;
fi;
