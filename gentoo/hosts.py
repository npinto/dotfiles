from fabric.api import task
from fabric.api import env


@task
def munctional():
    env.hosts += ['munctional%d' % i for i in xrange(1, 8 + 1)]
