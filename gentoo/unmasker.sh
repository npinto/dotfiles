#!/bin/bash

#
# This package unmasks a package and all its
# dependencies. It will not work with hard masked
# packages, only keyworded ones (~x86, ~amd64 for example).
# Also, it will not work if you try to unmask a package
# that requires a different EAPI than your installed portage version
# supports. You must then first manually install a newer portage
# version before trying to unmask.
#


#
# This function checks if a package is keyworded or not
# and returns a value depending on the result.
#
check_if_keyworded() {
    if [[ $(emerge --pretend --quiet $package_to_emerge | grep 'masked by:' | cut -d ' ' -f 5 | head -n 1) == "missing" ]]; then
	return 1
    else
	return 0
    fi
}

#
# This function does the actual unmasking.
#
do_unmasking() {
    echo 'Unmasking packages, this might take a while...'

    while ! emerge --pretend --quiet $package_to_emerge &> /dev/null; do
	spin
	package_to_unmask=$(emerge --pretend --quiet $package_to_emerge | grep 'masked by: ~' | cut -d ' ' -f 2 | head -n 1)
	echo "=$package_to_unmask" >> $outputpath/$outputfile
    done

    endspin

    echo "Unmasking done. Check $outputpath/$outputfile."
}

#
# Make sure only root can run our script
#
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi


if [[ -z "$1" ]]; then
	echo 'You need to supply the package you want to'
	echo 'unmask as an argument. Ex:'
	echo './unmasked.sh =category/package-x.y.z'
	exit
fi

#
# Variables we need
#
typeset package_to_emerge=$1
typeset package_to_unmask
typeset -i count=1
typeset outputfile
typeset outputpath=/etc/portage/package.keywords

#
# A spinner that shows while unmasking is taking place
# Thanks http://wooledge.org
#
typeset sp="/-\|"
typeset -i sc=0

spin() {
   printf "\b${sp:sc++:1}"
   ((sc==${#sp})) && sc=0
}
endspin() {
   printf "\r%s\n" "$@"
}

#
# Create unmasking file, naming it after the package to emerge
# (Split the package name at the '/' character)
#
outputfile=${package_to_emerge#*/} # Thanks http://anton.lr2.com :-)

#
# If /etc/portage/package.keywords does not exist, create it.
# If it exists and is a file, migrate contents.
#
if [[ ! -e "$outputpath" ]]; then
    echo "Creating necessary directories and files..."
    mkdir -p $outputpath
    touch $outputpath/$outputfile
fi

if [[ -f "$outputpath" ]]; then
    echo "$outputpath is a file."
    echo "I will now create a directory $outputpath"
    echo 'and move the contents of your old file into'
    echo "$outputpath/keywords-old"
    sleep 3s
    mv $outputpath /etc/portage/keywords-old
    mkdir -p $outputpath
    touch $outputpath/$outputfile
    mv /etc/portage/keywords-old $outputpath
fi

#
# Make sure package is keyworded. If not, abort.
#
if ! check_if_keyworded; then
    echo 'Package is missing keyword. I will not unmask this package'
    exit
else
    do_unmasking
fi
