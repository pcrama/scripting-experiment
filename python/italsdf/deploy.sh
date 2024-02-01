#!/usr/bin/env bash

if [ "$1" = "--for-tests" ];
then
    excludes='--exclude *.png --exclude *.html'
    shift
fi

destination="$1"
user="$2"
group="$3"
base_url="$4"
prefix_folder="$5"
deploy_folder="$6"
virtualenv_folder="$7"
admin_user="$8"
admin_pw="$9"

if [ -z "$destination" -o -z "$user" -o -z "$group" -o -z "$base_url" -o -z "$prefix_folder" -o -z "$deploy_folder" -o -z "$virtualenv_folder" ] ;
then
    echo -n "Missing parameters: $0 '$destination' '$user' '$group' '$base_url' '$prefix_folder' '$deploy_folder' '$virtualenv_folder'"
    if [ -n "$admin_user" -o -n "$admin_pw" ];
    then
        echo " '$admin_user' '$admin_pw'"
    else
        echo
    fi
    echo "Usage: $(basename "$0") <ssh-host> <user> <group> <https://base_url> <prefix_folder> <deploy_folder> <virtualenv_folder> [<admin-user> <admin-pw>]"
    exit 1
else
    folder="$prefix_folder/$deploy_folder"
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
    if [ -z "$excludes" ]; then
        default_index_html="$HOME/Downloads/srh-index.html"
        if [ -r "$default_index_html" ]; then
            index_html="$default_index_html"
        else
            index_html="index.html"
        fi
        dest_index_html="$staging_dir/index.html"
        (cd "$(dirname "$0")/input-form/build" \
             && cp *.js *.js.LICENSE.txt "$staging_dir" \
             && sed -n -e '/script defer src="/q' -e 'p' "$index_html" > "$dest_index_html" \
             && echo "<script>const ACTION_DEST=\"$base_url/$deploy_folder/post_reservation.cgi\"; const CONCERT_DATE=\"2023-03-25\";</script>" >> "$dest_index_html" \
             && for js in *.js ; do echo "<script defer src=\"$js\"></script>" >> "$dest_index_html" ; done \
             && sed -n -e '/script defer src="/ { s,.*</script>,,p ; q }' "$index_html" >> "$dest_index_html" \
             && sed -e '1,/script defer src="/d' "$index_html" >>"$dest_index_html" )
    fi
    tar cf - --exclude "#*" --exclude "*~" --exclude "*.bak" --exclude "*cache*" --exclude "index.org" --exclude ".dir-locals.el" $excludes \
        -C "$(dirname "$0")/app" \
        . \
        | tar xf - -C "$staging_dir"
    rm -f "$(dirname "$0")/app/gestion/index.html"
    find "$staging_dir" -type f '(' -name '*.cgi' -o -name '*.py' ')' -print0 | xargs -0 dos2unix
    if [ "$virtualenv_folder" = "no" ] ; then
        setup_venv=""
    else
        find "$staging_dir" -type f -name '*.cgi' -print0 | xargs -0 -n 1 sed -i -e '1s,.*,#!'"${virtualenv_folder%/}"'/bin/python3,'
        setup_venv="; python -m venv '${virtualenv_folder%/}'; '${virtualenv_folder%/}/bin/pip' install qrcode"
    fi
    find "$staging_dir" -type f -name '*.cgi' -print0 | xargs -0 chmod 744
    app_htaccess="$staging_dir/.htaccess"
    cat <<EOF > "$app_htaccess"
# Prevent directory listing https://stackoverflow.com/a/2530404:
Options -Indexes
# Try to improve caching of resources:
<filesMatch ".png\$">
    Header set Cache-Control "max-age=3600, public"
</filesMatch>
<filesMatch ".js\$">
    Header set Cache-Control "max-age=86400, public"
</filesMatch>
EOF
    dos2unix "$app_htaccess"
    tar czf - --"owner=$user" --"group=$group" -C "$staging_dir" . \
        | ssh "$destination" "mkdir -p '$folder'; rm -f '$folder'/*.js; tar xvzf - -C '$folder' $setup_password $setup_access $setup_venv"
    rm -r "$staging_dir" || echo "Unable to clean up staging_dir='$staging_dir'"
fi
