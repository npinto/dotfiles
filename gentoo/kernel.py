from fabric.api import run, cd
from fabric.api import task
from fabric.operations import reboot

@task
def emerge(version='3.0.6'):

    run("echo 'sys-kernel/gentoo-sources symlink' \
        > /etc/portage/package.use/gentoo-sources")
    run("emerge -q -uDN '=sys-kernel/gentoo-sources-%s'" % version)

    with cd("/usr/src/linux"):
        run("cp -vf /boot/config-`uname -r` .config")
        run("make oldconfig < /dev/null")
        run("make prepare")
        run("make -j 9")
        kernel_suffix = run("make modules_install \
                            | grep DEPMOD \
                            | awk '{print $2}'")
        run("cp -vf arch/x86_64/boot/bzImage \
            /boot/kernel-%s" % kernel_suffix)
        run("cp -vf System.map /boot/System.map-%s" % kernel_suffix)
        run("cp -vf .config /boot/config-%s" % kernel_suffix)

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

    reboot(180)

    run("uname -r")


@task
def fix_config():
    with cd("/boot/"):
        run("cp -vf /usr/src/linux/.config /boot/config-`uname -r`")
