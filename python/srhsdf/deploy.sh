#!/bin/sh

destination="$1"
user="$2"
group="$3"
folder="$4"
admin_user="$5"
admin_pw="$6"

if [ -z "$destination" -o -z "$user" -o -z "$group" -o -z "$folder" ] ;
then
    echo -n "Missing parameters: $0 '$destination' '$user' '$group' '$folder'"
    if [ -n "$admin_user" -o -n "$admin_pw" ];
    then
        echo " '$admin_user' '$admin_pw'"
    else
        echo
    fi
    echo "Usage: $(basename "$0") <ssh-host> <user> <group> <folder> [<admin-user> <admin-pw>]"
    exit 1
else
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
    staging_dir="$(mktemp --directory)"
    (cd "$(dirname "$0")/app/gestion" \
         && emacs --batch \
                  --eval "(progn (find-file \"index.org\") (org-html-export-to-html))")
    tar czf - --exclude "#*" --exclude "*~" --exclude "*.bak" --exclude "*cache*" --exclude "index.org" \
        -C "$(dirname "$0")/app" \
        . \
        | tar xzf - -C "$staging_dir"
    rm -f "$(dirname "$0")/app/gestion/index.html"
    find "$staging_dir" -type f '(' -name '*.cgi' -o -name '*.py' ')' -print0 | xargs -0 dos2unix
    tar cf - --"owner=$user" --"group=$group" -C "$staging_dir" . \
        | ssh "$destination" "mkdir -p '$folder'; tar xvf - -C '$folder' $setup_password $setup_access"
    rm -r "$staging_dir" || echo "Unable to clean up staging_dir='$staging_dir'"
fi
