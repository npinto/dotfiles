

export PATH=\$HOME/local/bin:\$PATH"
export LD_LIBRARY_PATH=\$HOME/local/lib:\$LD_LIBRARY_PATH"
export PYTHONVERSION=\$(python -c 'import sys; print sys.version[:3]')"
export PYTHONPATH_HOME=\$HOME/local/lib/python\$PYTHONVERSION/site-packages"
export PYTHONPATH=\$PYTHONPATH_HOME:\$PYTHONPATH"
export NPROCESSORS=\$(cat /proc/cpuinfo | grep processor | wc -l)"

