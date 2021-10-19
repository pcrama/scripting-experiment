#!/bin/sh

destination=$1
user=$2
group=$3
folder=$4

if [ -z "$destination" -o -z "$user" -o -z "$group" -o -z "$folder" ] ;
then
    echo "Missing parameters: $0 '$destination' '$user' '$group' '$folder'"
    echo "Usage: $(basename "$0") <ssh-host> <user> <group> <folder>"
else
    tar cf - --"owner=$user" --"group=$group" -C "$(dirname "$0")/app" . \
        | ssh "$destination" "mkdir -p '$folder'; tar xf - -C '$folder'"
fi
