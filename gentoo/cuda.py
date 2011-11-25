from fabric.api import task
from fabric.api import run


@task
def emerge(force='False'):

    force = eval(force)

    #emergecmd = 'emerge -q -DN'
    emergecmd = 'emerge -q -D'
    if not force:
        emergecmd += ' -u'

    # -- to get the init script
    # more info: https://bugs.gentoo.org/show_bug.cgi?id=376527
    #run("layman -l | grep nbigaouette || layman -a nbigaouette")
    run("layman -l | grep sekyfsr || layman -a sekyfsr")

    # -- keywords
    kwfn = "/etc/portage/package.keywords/cuda"
    run("rm -vf %s" % kwfn)
    pkgl = [
        'x11-drivers/nvidia-drivers',
        'dev-util/nvidia-cuda-toolkit',
        'dev-util/nvidia-cuda-sdk',
        'app-benchmarks/cuda_memtest',
        'dev-util/cuda-init-script',
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
        run(emergecmd + ' ' + pkg)

    # -- eselect
    run("eselect opengl set nvidia")

    # -- init script
    run("rc-update add cuda default")
    run("/etc/init.d/cuda restart")

    # -- load module
    run("rmmod -fv nvidia || exit 0")
    run("modprobe -v nvidia")

    # -- quick smoke tests
    run("lspci | grep VGA")
    run("/opt/cuda/sdk/C/bin/linux/release/deviceQuery < /dev/null")
    run("ls -l /dev/nvidia*")

    test()


@task
def test():

    run("ls /dev/nvidia? | wc -l")
