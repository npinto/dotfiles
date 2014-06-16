# -----------------------------------------------------------------------------
# -- CUDA related
# -----------------------------------------------------------------------------

if ! [[ "`uname`" == "Darwin" && "`uname -r`" == "12.4.0" ]]; then
    #test -d /Developer/NVIDIA/CUDA-6.0/bin && export PATH=$PATH:/Developer/NVIDIA/CUDA-6.0/bin/
    #test -d /Developer/NVIDIA/CUDA-6.0/lib && export PATH=$PATH:/Developer/NVIDIA/CUDA-6.0/lib/
    #test -d /Developer/NVIDIA/CUDA-6.0/lib64 && export PATH=$PATH:/Developer/NVIDIA/CUDA-6.0/lib64/
    test -d /usr/local/cuda/bin && export PATH=$PATH:/usr/local/cuda/bin;
    test -d /usr/local/cuda/lib && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib;
    test -d /usr/local/cuda/lib64 && export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64;
    # -- Gentoo
    test -d /opt/cuda/lib64 && export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/opt/cuda/lib64
fi;

