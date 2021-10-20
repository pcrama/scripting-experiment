#!/bin/sh

destination="$1"
user="$2"
group="$3"
folder="$4"

if [ -z "$destination" -o -z "$user" -o -z "$group" -o -z "$folder" ] ;
then
    echo "Missing parameters: $0 '$destination' '$user' '$group' '$folder'"
    echo "Usage: $(basename "$0") <ssh-host> <user> <group> <folder> [<admin-user> <admin-pw>]"
    exit 1
else
    admin_user="$5"
    admin_pw="$6"
    if [ -n "$admin_user" ];
    then
        protected_folder="$folder/gestion"
        password_file="$protected_folder/.htpasswd"
        if [ -z "$admin_pw" ];
        then
            echo "Missing password for admin user '$admin_user'."
            read -p "Password for '$admin_user' in '$destination:$protected_folder' " admin_pw || exit 2
        fi
        setup_password="; /usr/pkg/sbin/htpasswd -nb '$admin_user' '$admin_pw' > '$password_file'"
        access_file="$protected_folder/.htaccess"
        setup_access="; echo 'AuthUserFILE '\$(readlink -f \"\$(pwd)/$password_file\") > '$access_file'; echo 'AuthGroupFILE /dev/null' >> '$access_file'; echo 'AuthNAME \"SRH\"' >> '$access_file' ; echo 'AuthTYPE Basic' >> '$access_file' ; echo 'require user $admin_user' >> '$access_file'; echo 'allow from all' >> '$access_file'"
    else
        setup_password=""
        setup_access=""
    fi
    cd "$(dirname "$0")/app"
    dos2unix *.cgi *.py
    tar cf - --"owner=$user" --"group=$group" . \
        | ssh "$destination" "mkdir -p '$folder'; tar xvf - -C '$folder' $setup_password $setup_access"
fi
