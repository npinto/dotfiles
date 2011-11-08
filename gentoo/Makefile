
default: system tools scientific

# -- System
portage-dirs:
	mkdir -p /etc/portage/package.keywords
	mkdir -p /etc/portage/package.use
	mkdir -p /etc/portage/package.mask
	mkdir -p /etc/portage/package.unmask

# XXX:
# net-select (for ntpdate)
# lsof (system)

# -- Tools
tools: zsh vim tmux screen htop gparallel

zsh:
	emerge -uN zsh

vim: portage-dirs
	echo "app-editors/vim bash-completion vim-pager python ruby" >> /etc/portage/package.use/vim
	emerge -uN vim{,-core}

tmux:
	emerge -uN tmux

screen:
	emerge -uN screen

htop:
	emerge -uN htop

gparallel:
	emerge -uN sys-process/parallel

# -- Scientific
scientific: atlas numpy scipy

atlas:
	# -- blas
	emerge -uN cblas blas
	emerge -uN blas-atlas
	eselect blas set atlas-threads || exit 0
	eselect cblas set atlas-threads || exit 0
	# -- lapack
	emerge -uN lapack
	emerge -uN lapack-atlas
	eselect lapack set atlas || exit 0

numpy: portage-dirs atlas
	echo "=dev-python/numpy-1.6.1-r1" >> ${EPREFIX}/etc/portage/package.mask/numpy-1.6.1-r1
	echo "dev-python/numpy doc lapack test" >> ${EPREFIX}/etc/portage/package.use/numpy
	emerge -uN --onlydeps numpy
	FEATURES=test emerge -uN numpy

scipy: numpy
	emerge -uDN --onlydeps scipy
	# #FEATURES=test emerge -uN scipy
	emerge -uN scipy
