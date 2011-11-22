from fabric.api import run, cd


def host_type():
    run('uname -s')


def emerge_kernel(version='3.0.6'):

    run("echo 'sys-kernel/gentoo-sources symlink' \
        > /etc/portage/package.use/gentoo-sources")
    run("emerge -uDN '=sys-kernel/gentoo-sources-%s'" % version)

    with cd("/usr/src/linux"):
        run("cp -vf /boot/config-`uname -r` .config")
        run("make oldconfig < /dev/null")
        run("make -j 9")
        kernel_suffix = run("make modules_install \
                            | grep DEPMOD \
                            | awk '{print $2}'")
        run("cp -vf arch/x86_64/boot/bzImage \
            /boot/kernel-%s" % kernel_suffix)
        run("cp -vf System.map /boot/System.map-%s" % kernel_suffix)

    with cd("/boot/"):
        kernels = run('ls kernel-*').split()
        new_kernel_idx = kernels.index("kernel-%s" % kernel_suffix)
        menulst = [
            "default %d" % new_kernel_idx,
            "timeout 10",
        ]
        for kernel in kernels:
            menulst += [
                "",
                "title %s" % kernel,
                "root (hd0,5)",
                "kernel /boot/%s root=/dev/sda6" % kernel,
            ]
        menulst = ''.join([line + '\n' for line in menulst])

    with cd("/boot/grub"):
        run("cat > menu.lst.new << EOF\n" + menulst + "\nEOF\n")
        run("mv -vf menu.lst menu.lst.old")
        run("mv -vf menu.lst.new menu.lst")
        run("cat menu.lst")


def emerge_cuda():
    kwfn = "/etc/portage/package.keywords/cuda"
    run("rm -f %s" % kwfn)
    pkgl = [
        'x11-drivers/nvidia-drivers',
        'dev-util/nvidia-cuda-toolkit',
        'dev-util/nvidia-cuda-sdk',
        'app-benchmarks/cuda_memtest',
    ]
    for pkg in pkgl:
        run("echo '%s ~amd64' > %s" % (pkg, kwfn))
    run("rmmod -fv nvidia")
    run("modprobe -v nvidia")
    run("emerge -uDN %s" % ' '.join(pkgl))
