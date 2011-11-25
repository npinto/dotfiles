from fabric.api import run, cd, env
from fabric.api import task
from fabric.contrib.files import sed


@task
def sudo_with_password():
    sed("/etc/sudoers", ".*\%sudo.*ALL$", "%sudo ALL=(ALL) ALL")
    run("grep -e '^%sudo.*ALL$' /etc/sudoers")


@task
def dispatch_conf():
    # -- dependencies
    run("emerge -uDN -j rcs colordiff")

    # -- update configuration file
    conffn = "/etc/dispatch-conf.conf"
    sarl = [
        ("use-rcs=no", "use-rcs=yes"),
        ("replace-unmodified=no", "replace-unmodified=yes"),
    ]

    for search, replace in sarl:
        sed(conffn, search, replace)
        run("grep %s %s" % (replace, conffn))

    #run("yes 'u\n' | dispatch-conf", pty=True)
    #from fabric.operations import open_shell
    run("dispatch-conf")
    #open_shell("dispatch-conf")
