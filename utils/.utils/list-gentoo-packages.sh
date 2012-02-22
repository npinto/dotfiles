#!/bin/bash
#
# list-gentoo-packages.sh v0.2
# Copyright 2007-2009, Nikita Melnichenko [http://nikita.melnichenko.name]
# License: GPL-2 (http://opensource.org/licenses/gpl-license.php)
#
# List all installed Gentoo packages with USE flags.

# generate use flags for package $1 (official, but very slow)
function portage_gen_use_flags_by_equery ()
{
	equery -N -C uses '='"$1" | grep '^ [+-]' | awk '{ printf "%s%s\n", $2, $3 }'
}

# generate use flags for package $1 (unofficial, but fast)
function portage_gen_use_flags_from_var_db_pkg ()
{
	if ! [ -f /var/db/pkg/"$1"/IUSE ]
	then
		return
	fi

	local use_flags=`cat /var/db/pkg/"$1"/USE`
	for iuse in `cat /var/db/pkg/"$1"/IUSE | sed -e "s/ /\n/g" | LC_ALL=C sort | uniq`
	do
		iuse=`echo "$iuse" | sed -e "s/^[+-]//g"`
		used=0
		for use in $use_flags
		do
			if [ "$use" == "$iuse" ]
			then
				used=1
				break
			fi
		done

		if [ $used -eq 0 ]
		then
			echo -n '-'
		else
			echo -n '+'
		fi
		echo $iuse
	done
}

# generate use flags for package $1
function portage_gen_use_flags ()
{
	portage_gen_use_flags_from_var_db_pkg "$1"
}

# generate list of all installed packages with their USE flags
function portage_list_installed ()
{
	find /var/db/pkg -mindepth 2 -type d | sed -e 's|^/var/db/pkg/||' | LC_ALL=C sort | while read pkg
	do
		echo -n "$pkg"
		portage_gen_use_flags "$pkg" | LC_ALL=C sort | while read flag
		do
			echo -n " $flag"
		done
		echo
	done
}

portage_list_installed
