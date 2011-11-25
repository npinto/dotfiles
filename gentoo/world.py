from fabric.api import run, cd, env
from fabric.api import task
from fabric.contrib.files import sed


@task
def emerge(ask=True):

    ask = eval(ask)

    emergecmd = 'emerge -q'
    if ask:
        emergecmd += ' -a'

    glsacheckl = run("glsa-check -t all")
    run("glsa-check -f all")
    if glsacheckl != 'This system is not affected by any of the listed GLSAs':
        run("glsa-check -p" + glsacheckl)
        run("glsa-check -f" + glsacheckl)

    out = run(emergecmd + " -vuDN -j --with-bdeps y --keep-going world system")
    if 'Nothing to merge' not in out:
        run(emergecmd + " -v --depclean")
        if ask:
            run("revdep-rebuild -v -- --ask")
        else:
            run("revdep-rebuild -v --")
        run("eclean-dist -d")
        run("eix-test-obsolete")
    #dispatch-conf'\'
