#!/bin/bash
#
# Build and iPhone Simulator Helper Script
# Shazron Abdullah 2011
#
# WARN: - if your .xcodeproj name is not the same as your .app name, 
#		    this won't work without modifications
#		- you must run this script in where your .xcodeproj file is

PROJECTNAME=$1
CONFIGURATION=$2
LOGFILE=$3

function help
{
	echo "Usage: $0 <projectname> [configuration] [logname]"
	echo "<projectname>		name of your .xcodeproj file (and your .app as well)"
	echo "[configuration]	(optional) Debug or Release, defaults to Debug"
	echo "[logname]			(optional) the log file to write to. defaults to stderror.log"
}

# check first argument
if [ -z "$PROJECTNAME" ] ; then
	help
	exit 1
fi

# check second argument, default to "Debug"
if [ -z "$CONFIGURATION" ] ; then
	CONFIGURATION=Debug
fi

# check third argument, default to "stderror.log"
if [ -z "$LOGFILE" ] ; then
	LOGFILE=stderr.log
fi

# backup existing logfile (start fresh each time)
if [ -f $LOGFILE ]; then
mv $LOGFILE $LOGFILE.bak	
fi

touch -cm www
xcodebuild -configuration $CONFIGURATION -sdk iphonesimulator -project $PROJECTNAME.xcodeproj
ios-sim launch build/$CONFIGURATION-iphonesimulator/$PROJECTNAME.app --stderr $LOGFILE --exit
osascript -e "tell application \"iPhone Simulator\" to activate"
tail -f $LOGFILE 
