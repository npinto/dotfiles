from fabric.api import run, cd
from fabric.api import task


@task
def eix_sync():
    """Update portage tree"""
    run("eix-sync -q")


@task
def init():

    # -- update dotfiles
    with cd("~/dotfiles"):
        run("git remote add readonly git://github.com/npinto/dotfiles.git || exit 0")
        run("git pull readonly master")

    # -- disable keychain
    run("touch ~/.no_keychain")

    # -- update portage tree
    eix_sync()
