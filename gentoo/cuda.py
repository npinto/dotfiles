from fabric.api import task
from fabric.api import run


@task
def emerge(force=False):

    force = eval(force)

    emergecmd = 'emerge -q'
    if not force:
        emergecmd += ' -u'

    # -- keywords
    kwfn = "/etc/portage/package.keywords/cuda"
    run("rm -vf %s" % kwfn)
    pkgl = [
        'x11-drivers/nvidia-drivers',
        'dev-util/nvidia-cuda-toolkit',
        'dev-util/nvidia-cuda-sdk',
        #'app-benchmarks/cuda_memtest',
    ]
    for pkg in pkgl:
        run("echo '%s ~amd64' >> %s" % (pkg, kwfn))

    # -- use
    run("echo 'dev-util/nvidia-cuda-toolkit debugger profiler doc' "
        "> /etc/portage/package.use/cuda")

    run("echo 'dev-util/nvidia-cuda-sdk opencl' "
        "> /etc/portage/package.use/cuda")

    # -- emerge
    for pkg in pkgl:
        run(emergecmd + pkg)

    # -- load module
    run("rmmod -fv nvidia || exit 0")
    run("modprobe -v nvidia")

    # -- quick smoke tests
    run("lspci | grep VGA")
    run("/opt/cuda/sdk/C/bin/linux/release/deviceQuery < /dev/null")
    run("ls /dev/nvidia*")

    test()


@task
def test():

    run("ls /dev/nvidia? | wc -l")
