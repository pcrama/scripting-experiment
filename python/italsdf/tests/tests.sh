#!/bin/bash

set -e

function or_default {
    if [ -n "$1" ];
    then
        echo "$1"
    else
        echo "$2"
    fi
}

if [ "$1" == "-x" ];
then
    dash_x=' -x'
    shift
else
    dash_x=''
fi

if [ "$1" == "-f" ];
then
    skip_deploy=' -f'
    shift
else
    skip_deploy=''
fi

base_url="$1"
host_path_prefix="$2"
destination="$3"
user="$4"
group="$5"
pseudo_random="$(date '+%s')"
admin_user="$(or_default "$6" "user_$pseudo_random")"
admin_pw="$(or_default "$7" "pw_$pseudo_random")"
bank_account="BExx-$pseudo_random"
info_email="mrx.$pseudo_random@example.com"

if [ -z "$skip_deploy" -a '(' -z "$host_path_prefix" -o -z "$base_url" ')' ];
then
    echo "Missing parameters: '$0'$dash_x$skip_deploy '$base_url' '$host_path_prefix' '$destination' '$user' '$group' '$admin_user' '$admin_pw'"
    echo "Usage: $(basename "$0") [-x] [-f] <base-url> <host-path-prefix> <ssh-host> <user> <group> [<admin-user> <admin-pw>]"
    exit 1
fi

# Where 'golden' reference files are stored
golden="$(dirname "$0")/golden"

# Make web request
# - $1: end point
# - $2: output file
# - $3: curl options
# - $4: credentials
function _do_curl {
    local end_point
    case "$1" in
        http://* | https://* ) if [ -n "$4" ] ; then
                                   die "Unable to handle credentials in _do_curl with end_point='$1'"
                               fi
                               end_point="$1" ;;
        * ) end_point="https://$4$base_url/$folder/$1" ;;
    esac
    curl "$end_point" $3 \
        | sed -e "s;$folder;TEST_DIR;g" -e "s;$base_url;TEST_HOST;g" -e "s;mailto:$info_email;TEST_EMAIL;g"\
              > "$2"
}

function do_curl {
    _do_curl "$1" "$2" "$3"
}

function do_curl_as_admin {
    _do_curl "$1" "$2" "$3" "$admin_user:$admin_pw@"
}

function assert_redirect_to_concert_page_for_integration_test
{
    local test_stderr
    test_stderr="$1"
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr" \
        || die "Not a redirect: $test_stderr"
    grep -q '^< Content-Length: 0' "$test_stderr" \
        || die "Content-Length != 0: $test_stderr"
    grep -q '^< Location: https://www.srhbraine.be/soiree-italienne/' "$test_stderr" \
        || die "Target is not concert page: $test_stderr"
}

function assert_redirect_to_concert_page_for_local_test
{
    local test_name test_output
    test_name="$1"
    test_output="$2"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    grep -q --fixed-strings 'Location: https://www.srhbraine.be/' "$test_output" || die "$test_name not redirecting to correct site in $test_output"
}

function do_curl_with_redirect
{
    local credentials end_point test_output options test_stderr location
    if [ "$1" = "--admin" ];
    then
        credentials="$admin_user:$admin_pw@"
        shift
    else
        credentials=""
    fi
    end_point="$1"
    test_output="$2"
    options="$3"
    test_stderr="$test_output.stderr"
    _do_curl "$end_point" "$test_output" "$options --verbose" "$credentials" \
             2> "$test_stderr"
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr"
    grep -q '^< Content-Length: 0' "$test_stderr"
    location="$(tr -d '\r' < "$test_stderr" | sed -n -e 's/^< Location: *//p')"
    do_curl "$location" "$test_output"
    echo "$location"
}

function die {
    >&2 echo $1
    exit 2
}

function get_db_file {
    scp "$destination:$ssh_app_folder/db.db" "$db_file"
}

function put_db_file {
    scp "$db_file" "$destination:$ssh_app_folder/db.db"
}

function sql_query {
    echo "$1" | sqlite3 "$db_file"
}

function count_reservations {
    sql_query "SELECT COUNT(*) FROM reservations;"
}

function count_csrfs {
    sql_query "SELECT COUNT(*) FROM csrfs;"
}

function count_payments {
    sql_query "SELECT COUNT(*) FROM payments;"
}

function get_user_of_csrf_token {
    sql_query "SELECT user FROM csrfs WHERE token='$1';"
}

function get_csrf_token_of_user {
    # Ignores IP address... but there should be only one anyway.
    sql_query "SELECT token FROM csrfs WHERE user='$1' ORDER BY timestamp DESC LIMIT 1;"
}

function do_diff {
    local reference
    reference="$golden/$(basename "$1")"
    if diff -wq "$1" "$reference" ;
    then
        echo "Content of '$1' is as expected."
    else
        echo "diff '$1' '$reference'"
        die "File comparison failed, accept with
    cp '$1' '$reference'"
    fi
}

function generic_test_valid_reservation_for_test_date
{
    local test_name spectator_name spectator_email places concert_date outside_fondus outside_assiettes outside_bolo outside_scampis outside_tiramisu outside_tranches inside_assiettes_bolo_tiramisu gdpr_accepts_use total_reservations_count test_output
    test_name="$1"
    spectator_name="$2"
    spectator_email="$3"
    places="$4"
    concert_date="$5"
    outside_fondus="$6"
    outside_assiettes="$7"
    outside_bolo="$8"
    outside_scampis="$9"; shift
    outside_tiramisu="$9"; shift
    outside_tranches="$9"; shift
    inside_assiettes_bolo_tiramisu="$9"; shift
    gdpr_accepts_use="$9"; shift
    total_reservations_count="$9"
    test_output="$test_dir/$test_name.html"
    do_curl_with_redirect 'post_reservation.cgi' \
                          "$test_output" \
                          "-X POST -F name=$spectator_name -F email=$spectator_email -F places=$places -F date=$concert_date -F outside_fondus=$outside_fondus -F outside_assiettes=$outside_assiettes -F outside_bolo=$outside_bolo -F outside_scampis=$outside_scampis -F outside_tiramisu=$outside_tiramisu -F outside_tranches=$outside_tranches -F inside_assiettes=$inside_assiettes_bolo_tiramisu -F inside_bolo=$inside_assiettes_bolo_tiramisu -F inside_tiramisu=$inside_assiettes_bolo_tiramisu -F gdpr_accepts_use=$gdpr_accepts_use"
    get_db_file
    do_diff "$test_output"
    if [ "$(count_reservations)" != "$total_reservations_count" ]; then
        die "test_$test_name: Reservations table should contain $total_reservations_count row."
    fi
    if [ "${spectator_name:0:1}" = "<" ]; then
        # Handle curl(1) syntax reading parameter values from file: strip
        # leading `<' character and read file content
        spectator_name="$(cat "${spectator_name:1}")"
    fi
    if [ "${spectator_email:0:1}" = "<" ]; then
        # Handle curl(1) syntax reading parameter values from file: strip
        # leading `<' character and read file content
        spectator_email="$(cat "${spectator_email:1}")"
    fi
    if [ "$(sql_query "SELECT name, email, places, date, outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches, inside_assiettes, inside_bolo, inside_scampis, inside_tiramisu, gdpr_accepts_use, active FROM reservations WHERE name = '$spectator_name' AND email = '$spectator_email' AND places = $places;")" \
             != "$spectator_name|$spectator_email|$places|$concert_date|$outside_fondus|$outside_assiettes|$outside_bolo|$outside_scampis|$outside_tiramisu|$outside_tranches|$inside_assiettes_bolo_tiramisu|$inside_assiettes_bolo_tiramisu|0|$inside_assiettes_bolo_tiramisu|$gdpr_accepts_use|1" \
       ]; then
        die "test_$test_name: Wrong data saved in DB"
    fi
    if [ "$(count_csrfs)" -gt "1" ]; then
        die "test_$test_name: CSRF problem: new CSRF token created."
    fi
    echo "test_$test_name: ok"
}

function generic_test_new_reservation_without_valid_CSRF_token_fails
{
    local test_name csrf_arg test_output test_stderr
    test_name="$1"
    csrf_arg="$2"
    test_output="$test_dir/$test_name.will-be-empty"
    test_stderr="$test_dir/$test_name.stderr.log"
    do_curl_as_admin 'gestion/add_unchecked_reservation.cgi' \
                     "$test_output" \
                     "-X POST -F name=$test_name -F email=ByAdminNoCsrf@email.com -F date=2099-01-01 -F outside_fondus=20 -F outside_assiettes=20 -F outside_bolo=20 -F outside_scampis=20 -F outside_tiramisu=20 -F outside_tranches=20 places=3 $csrf_arg --verbose" \
                     2> "$test_stderr"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    assert_redirect_to_concert_page_for_integration_test "$test_stderr"
    echo "test_$test_name: ok"
}

function generic_test_generate_tickets_without_valid_CSRF_token_fails
{
    local test_name csrf_arg test_output test_stderr
    test_name="$1"
    csrf_arg="$2"
    test_output="$test_dir/$test_name.will-be-empty"
    test_stderr="$test_dir/$test_name.stderr.log"
    do_curl_as_admin 'gestion/generate_tickets.cgi' \
                     "$test_output" \
                     "-X POST -F outside_fondus=20 -F outside_assiettes=20 -F outside_bolo=20 -F outside_scampis=20 -F outside_tiramisu=20 -F outside_tranches=20 places=3 $csrf_arg --verbose" \
                     2> "$test_stderr"
    assert_redirect_to_concert_page_for_integration_test "$test_stderr"
    echo "test_$test_name: ok"
}

function get_csrf_token_from_html
{
    sed -n -e 's/.*CSRF_TOKEN *= *.\([a-f0-9A-F]*\).;.*/\1/p' "$1"
}

# Assumes up to date DB is available (see get_db_file), validates that the
# CSRF token is included.  Output to stdout.
function make_list_reservations_output_deterministic
{
    local input substitutions csrf_token
    input="$1"
    csrf_token="$2"
    if [ -z "$csrf_token" ];
    then
        die "No csrf_token in '$input'"
    else
        sed -e 's/\(CSRF_TOKEN *= *.\)'"$csrf_token"'/\1CSRF_TOKEN/g' \
            -e "s/$admin_user/TEST_ADMIN/g" \
            -e "$(date +"s,%d/%m/%Y [012][0-9]:[0-5][0-9]</td></tr>,TIMESTAMP</td></tr>,g")" \
            "$input"
    fi
}

app_dir="$(dirname "$0")/../app"
admin_sub_dir="gestion"

function simulate_cgi_request
{
    local method script_name query_string
    method="$1"
    script_name="$2"
    query_string="$3"
    shift 3
    # env "$(python3 -c 'import urllib3; body, header = urllib3.encode_multipart_formdata({"csrf_token": "abcd01234e", "csv_file": ("test.csv", "a;b\n0;1"), "submit": "Importer les extraits de compte"}); print(f"CONTENT_TYPE={header!r} CONTENT_STDIN=\"{body.decode('"'utf8'"')}\"")')"
    echo "${CONTENT_STDIN:-}" | (
        cd "$app_dir/$(dirname "$script_name")" \
            && env TEMP="$test_dir" \
                   REQUEST_METHOD="$method" \
                   QUERY_STRING="$query_string" \
                   SERVER_NAME=example.com \
                   SCRIPT_NAME="$script_name" \
                   "$@" \
                   python3 "$(basename "$script_name")"
    )
}

function capture_cgi_output
{
    local ignore_cgitb test_name method script_name query_string test_output
    if [ "$1" = "--ignore-cgitb" ]; then
        ignore_cgitb="$1"
        shift
    else
        ignore_cgitb=""
    fi
    test_name="$1"
    method="$2"
    script_name="$3"
    query_string="$4"
    shift 4
    if [ -z "$5" ]; then
        test_output="$test_dir/$test_name.log"
    else
        test_output="$5"
        shift
    fi
    if ! simulate_cgi_request "$method" "$script_name" "$query_string" "$@" > "$test_output" ; then
        [ -z "$ignore_cgitb" ] && die "$test_name CGI execution problem, look in $test_output"
    fi
    echo "$test_output"
}

function capture_admin_cgi_output
{
    local ignore_cgitb test_name method script_name query_string test_output
    if [ "$1" = "--ignore-cgitb" ]; then
        ignore_cgitb="$1"
        shift
    else
        ignore_cgitb=""
    fi
    test_name="$1"
    method="$2"
    script_name="$3"
    query_string="$4"
    shift 4
    if [ -z "$5" ]; then
        test_output="$test_dir/$test_name.log"
    else
        test_output="$5"
        shift
    fi
    if ! simulate_cgi_request "$method" "$admin_sub_dir/$script_name" "$query_string" REMOTE_USER="$admin_user" REMOTE_ADDR="1.2.3.4" "$@" > "$test_output" ; then
        [ -z "$ignore_cgitb" ] && die "$test_name admin CGI execution problem, look in $test_output"
    fi

    echo "$test_output"
}

function assert_html_response
{
    local no_banner test_name test_output pattern
    if [ "$1" == "--no-banner" ]; then
        no_banner="$1"
        shift
    else
        no_banner=""
    fi
    test_name="$1"
    test_output="$2"
    grep -q "Content-Type: text/html; charset=utf-8" "$test_output" || die "$test_name No Content-Type in $test_output"
    grep -q '<!DOCTYPE HTML><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>' "$test_output" || die "$test_name no HTML preamble boilerplate in $test_output"
    if [ -z "$no_banner" ]; then
        grep -q '</title><link rel="stylesheet" href="styles.css"></head><body><div id="branding" role="banner"><h1 id="site-title">Société Royale d'\''Harmonie de Braine-l'\''Alleud</h1><img src="https://www.srhbraine.be/wp-content/uploads/2019/10/site-en-tete.jpg" width="940" height="198" alt=""></div>' "$test_output" || die "$test_name no banner in $test_output"
    else
        if grep -q '<h1.*Braine.*Alleud</h1><img src' "$test_output"; then
            die "$test_name banner in $test_output"
        fi
    fi
    shift 2
    for pattern in "$@" ; do
        grep -q "$pattern" "$test_output" || die "$test_name \`\`$pattern'' not found in $test_output"
    done
}

function assert_not_in_html_response
{
    local test_name test_output pattern
    test_name="$1"
    test_output="$2"
    grep -q "Content-Type: text/html; charset=utf-8" "$test_output" || die "$test_name No Content-Type in $test_output"
    grep -q '<!DOCTYPE HTML><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>' "$test_output" || die "$test_name no HTML preamble boilerplate in $test_output"
    shift 2
    for pattern in "$@" ; do
        if grep -q "$pattern" "$test_output" ; then
            die "$test_name \`\`$pattern'' should not be in HTML $test_output"
        fi
    done
}

function assert_csv_response
{
    local test_name test_output pattern
    test_name="$1"
    test_output="$2"
    grep -q "Content-Type: text/csv; charset=utf-8" "$test_output" || die "$test_name No Content-Type in $test_output"
    shift 2
    for pattern in "$@" ; do
        grep -q "$pattern" "$test_output" || die "$test_name \`\`$pattern'' not found in $test_output"
    done
}

# Test definitions

function test_01_locally_valid_post_reservation
{
    local test_name test_output uuid_hex
    test_name="test_01_locally_valid_post_reservation"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi 'name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidebolo=4&insideextradish=3&bolokids=8&extradishkids=9&outsidemainstarter=10&outsideextrastarter=11&outsidebolo=12&outsideextradish=13&outsidedessert=14&gdpr_accepts_use=true&date=2099-01-01')"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        [ "$(count_reservations)" = 1 ] || die "$test_name: Reservation count"
        data=$(sql_query "SELECT name, email, extra_comment, date, places, inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish, outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert, kids_bolo, kids_extra_dish FROM reservations WHERE uuid='$uuid_hex'")
        [ "$data" = "test|i@example.com|commentaire|2099-01-01|1|2|5|4|3|10|11|12|13|14|8|9" ] || die "$test_name Wrong data inserted for $uuid_hex"
    else
        die "$test_name uuid_hex not found in $test_output"
    fi
}

# Invalid input to show_reservation.cgi redirects to main website
function test_02_locally_invalid_show_reservation
{
    local test_name test_output
    test_name="test_02_locally_invalid_show_reservation"
    test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "")"
    assert_redirect_to_concert_page_for_local_test "$test_name" "$test_output"
}

# Reuse reservation from test_01 to look at output
function test_03_locally_display_existing_reservation
{
    local test_name test_output uuid_hex
    test_name="test_03_locally_display_existing_reservation_1"
    uuid_hex=$(sql_query "SELECT uuid FROM reservations LIMIT 1")
    test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
    assert_html_response "$test_name" "$test_output" \
                         "Merci de nous avoir " \
                         "Le prix total est de " \
                         "Nous vous saurions "

    # insert reservation for places without any food reservation, using the
    # opportunity to double-check on HTML escaping.
    test_name="test_03_locally_display_existing_reservation_2"
    sql_query 'INSERT INTO reservations VALUES ("<name>", "email@domain.com", "<this> & </that>'\''""", 2, "2099-01-01", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, "", "'"$test_name"'", "'$(date +"%s")'", 1, "<a test&>")'
    test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$test_name")"
    assert_html_response "$test_name" "$test_output" \
                         "La commande des repas se fera.*paiement mobile mais accepterons" \
                         " &lt;name&gt; "
}

# Some validation testing
function test_04_locally_invalid_post_reservation
{
    local test_name test_output uuid_hex inside_menu_mismatch_query_string invalid_email_query_string query_string
    test_name="test_04_locally_invalid_post_reservation"

    inside_menu_mismatch_query_string='name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidebolo=0&insideextradish=3&bolokids=8&extradishkids=9&outsidemainstarter=10&outsideextrastarter=11&outsidebolo=12&outsideextradish=13&outsidedessert=14&gdpr_accepts_use=true&date=2099-01-01'
    query_string="$inside_menu_mismatch_query_string"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi "$query_string")"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        die "$test_name reservation $uuid_hex created for invalid $query_string"
    fi
    assert_html_response "$test_name" "$test_output" \
                         "invalides dans le formulaire" \
                         "ne correspond pas au nombre de plats"

    invalid_email_query_string='name=test&email=example.com%40&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidebolo=4&insideextradish=3&bolokids=8&extradishkids=9&outsidemainstarter=10&outsideextrastarter=11&outsidebolo=12&outsideextradish=13&outsidedessert=14&gdpr_accepts_use=true&date=2099-01-01'
    query_string="$invalid_email_query_string"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi "$query_string")"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        die "$test_name reservation $uuid_hex created for invalid $query_string"
    fi
    assert_html_response "$test_name" "$test_output" \
                         "invalides dans le formulaire" \
                         "adresse email.*n'a pas le format requis"
}

function test_05_locally_list_reservations
{
    local test_name test_output js_files uuid_hex bank_transaction_number
    test_name="test_05_locally_list_reservations"
    test_output="$(capture_admin_cgi_output "$test_name" GET list_reservations.cgi "")"
    if js_files="$(ls $(dirname "$0")/../input-form/build/*.js 2> /dev/null)" ; then
        js_file_patterns="$(basename -a $js_files | sed -e 's;^;<script.defer.src=.*;')"
    else
        js_file_patterns=""
        # die "Build the JS application first!"
    fi
    # Check that the output contains a link to the payment info and the transaction number
    uuid_hex="$(sql_query 'select uuid from reservations limit 1')"
    bank_transaction_number="$(sql_query "select bank_id from reservations where uuid='$uuid_hex'" | sed -e 's;\(...\)\(....\)\(.....\);+++\1/\2/\3+++;')"
    assert_html_response "$test_name" "$test_output" \
                         "https://example.com/gestion/list_reservations\\.cgi" \
                         "<li>12 Tomates Mozzarella</li>" \
                         "<li>16 Croquettes au fromage</li>" \
                         "<li>16 Spaghettis bolognaise</li>" \
                         "<li>16 Spaghettis aux légumes</li>" \
                         "<li>8 Spag\\. bolognaise (enfants)</li>" \
                         "<li>9 Spag\\. aux légumes (enfants)</li>" \
                         "<li>38 Assiettes de 3 Mignardises</li>" \
                         "<a href=[^ ]*show_reservation[^ ]*$uuid_hex" \
                         "$bank_transaction_number" \
                         '<li><a href="list_payments.cgi">Gérer les paiements</a></li>' \
                         '<li><a href="generate_tickets.cgi">Générer les tickets nourriture pour impression</a></li>' \
                         'const CSRF_TOKEN = "' \
                         '<div id="elmish-app"></div><script>const ACTION_DEST = "add_unchecked_reservation.cgi";' \
                         $js_file_patterns
}

function test_06_locally_add_unchecked_reservation_CSRF_failure
{
    local test_name test_output
    test_name="test_06_locally_add_unchecked_reservation_CSRF_failure"
    test_output="$(capture_admin_cgi_output "$test_name" POST add_unchecked_reservation.cgi 'name=Qui+m%27appelle%3F&extraComment=02%2F123.45.67&places=1&insidemainstarter=1&insideextrastarter=0&insidebolo=0&insideextradish=1&bolokids=0&extradishkids=0&outsidemainstarter=0&outsideextrastarter=0&outsidebolo=0&outsideextradish=0&outsidedessert=0&csrf_token=this-is-not-a-valid-CSRF-token&date=2023-03-25')"
    assert_redirect_to_concert_page_for_local_test "$test_name" "$test_output"
}

function test_07_locally_add_unchecked_reservation
{
    local test_name test_output csrf uuid_hex
    test_name="test_07_locally_add_unchecked_reservation"
    csrf="$(sql_query "SELECT token FROM csrfs LIMIT 1")"
    test_output="$(capture_admin_cgi_output "$test_name" POST add_unchecked_reservation.cgi "name=Qui+m%27appelle%3F&extraComment=02%2F123.45.67&places=1&insidemainstarter=1&insideextrastarter=0&insidebolo=0&insideextradish=1&bolokids=0&extradishkids=0&outsidemainstarter=0&outsideextrastarter=0&outsidebolo=0&outsideextradish=0&outsidedessert=0&csrf_token=$csrf&date=2023-03-25")"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        [ "$(count_reservations)" = 3 ] || die "$test_name: Reservation count"
        data=$(sql_query "SELECT name, email, extra_comment, date, places, inside_main_starter, inside_extra_starter, inside_bolo, inside_extra_dish, outside_main_starter, outside_extra_starter, outside_bolo, outside_extra_dish, outside_dessert, kids_bolo, kids_extra_dish FROM reservations WHERE uuid='$uuid_hex'")
        [ "$data" = "Qui m'appelle?||02/123.45.67|2023-03-25|1|1|0|0|1|0|0|0|0|0|0|0" ] || die "$test_name Wrong data inserted for $uuid_hex"
    else
        die "$test_name uuid_hex not found in $test_output"
    fi
}

function test_08_locally_GET_generate_tickets
{
    local test_name test_output csrf
    test_name="test_08_locally_GET_generate_tickets"
    test_output="$(capture_admin_cgi_output "$test_name" GET generate_tickets.cgi "")"
    csrf="$(sql_query "SELECT token FROM csrfs LIMIT 1")"
    assert_html_response "$test_name" "$test_output" \
                         "Impression des tickets pour la nourriture" \
                         'name="csrf_token" value="'"$csrf"'"' \
                         '<form method="POST"' \
                         'label for="main_starter">.*:</label><input type="number" id="main_starter" name="main_starter"' \
                         'label for="extra_starter">.*:</label><input type="number" id="extra_starter" name="extra_starter"' \
                         'label for="bolo">.*:</label><input type="number" id="bolo" name="bolo"' \
                         'label for="extra_dish">.*:</label><input type="number" id="extra_dish" name="extra_dish"' \
                         'label for="kids_bolo">.*:</label><input type="number" id="kids_bolo" name="kids_bolo"' \
                         'label for="kids_extra_dish">.*:</label><input type="number" id="kids_extra_dish" name="kids_extra_dish"' \
                         'label for="dessert">.*:</label><input type="number" id="dessert" name="dessert"'

    test_name="${test_name}_unauthenticated"
    test_output="$(capture_cgi_output "$test_name" GET gestion/generate_tickets.cgi "")"
    assert_redirect_to_concert_page_for_local_test "$test_name" "$test_output"
}

function test_09_locally_POST_generate_tickets
{
    local test_name test_output csrf
    test_name="test_09_locally_POST_generate_tickets"
    test_output="$(capture_admin_cgi_output "${test_name}_no_csrf" POST generate_tickets.cgi "")"
    assert_redirect_to_concert_page_for_local_test "${test_name}_no_csrf" "$test_output"

    csrf="$(sql_query "SELECT token FROM csrfs LIMIT 1")"
    test_output="$(capture_admin_cgi_output --ignore-cgitb "${test_name}_only_csrf" POST generate_tickets.cgi "csrf_token=$csrf")"
    grep -q "RuntimeError: Not enough tickets" "$test_output" || die "${test_name}_only_csrf should contain RuntimeError because a lack of tickets"

    test_output="$(capture_admin_cgi_output "${test_name}" POST generate_tickets.cgi "csrf_token=$csrf&main_starter=20&extra_starter=41&bolo=42&extra_dish=73&kids_bolo=74&kids_extra_dish=75&dessert=76")"
    assert_html_response --no-banner "$test_name" "$test_output" \
                         "<title>Liste des tickets à imprimer</title>" \
                         "Qui m'appelle[^:]*: 1 place.*pour 3 tickets: 1m[+0c]* Tomate Mozzarella, 1m[+0c]* Spaghetti aux légumes, 1m[+0c]* Assiette de 3 Mignardises" \
                         "Vente libre</div><div>Tomate Mozzarella=7, Croquettes au fromage=25, Spaghetti bolognaise=26, Spaghetti aux légumes=56, Spag. bolognaise (enfants)=66, Spag. aux légumes (enfants)=66, Assiette de 3 Mignardises=37</div>"
}

function test_10_locally_list_payments_before_adding_any_to_db
{
    local test_name test_output uuid_hex csrf_token
    test_name="test_10_locally_list_payments_before_adding_any_to_db"
    test_output="$(capture_admin_cgi_output "${test_name}" GET list_payments.cgi "")"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    assert_html_response "$test_name" "$test_output" \
                         '<input type="hidden" id="csrf_token" name="csrf_token" value="'"$csrf_token"'">' \
                         '<input type="file" id="csv_file" name="csv_file">' \
                         '<th>Réservation</th></tr></table><hr><ul><li><a href="list_reservations.cgi">Liste des réservations</a></li><li><a href="generate_tickets.cgi">'
}

function test_11_locally_reservation_example
{
    local test_name test_output
    test_name="test_11_locally_reservation_example"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi 'name=realperson&email=i%40gmail.com&extraComment=commentaire&places=2&insidemainstarter=1&insideextrastarter=0&insidebolo=1&insideextradish=0&bolokids=1&extradishkids=0&outsidemainstarter=0&outsideextrastarter=1&outsidebolo=0&outsideextradish=0&outsidedessert=3&gdpr_accepts_use=true&date=2023-03-25')"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Le prix total est de 73.00 € pour le repas" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">Dessert: 5 Assiettes de 3 Mignardises</li>" \
                             "Nous vous saurions gré de déjà verser cette somme avec la communication structurée"

        sql_query 'INSERT INTO payments VALUES (NULL, 2.3, 350, "partial payment", "'"$uuid_hex"'", "src_id_0", "BE001100", "realperson", "Accepté", "unit test admin user", "1.2.3.4")'
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Le prix total est de 73.00 € pour le repas dont 69.50 € sont encore dûs" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">Dessert: 5 Assiettes de 3 Mignardises</li>" \
                             "Nous vous saurions gré de déjà verser cette somme avec la communication structurée"

        sql_query 'INSERT INTO payments VALUES (NULL, 86405.5, 6950, "partial payment", "'"$uuid_hex"'", "src_id_1", "BE001100", "realperson", "Accepté", "unit test admin user", "1.2.3.4")'
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Merci d'avoir déjà réglé l'entièreté des 73.00 € dûs" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">Dessert: 5 Assiettes de 3 Mignardises</li>"
        assert_not_in_html_response "$test_name" "$test_output" "verser cette somme avec la communication structurée"
    else
        die "$test_name unable to extract uuid_hex"
    fi
}

function test_12_locally_export_csv
{
    local test_name test_output
    test_name="test_12_locally_export_csv"
    test_output="$(capture_admin_cgi_output "${test_name}" GET export_csv.cgi "")"
    assert_csv_response "$test_name" "$test_output" \
                        "realperson,2,1,0,1,0,1,1,0,1,0,1,0,0,3,73.00 €,0.00 €,commentaire,i@gmail.com,i@gmail.com,1," \
                        '<name>,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0.00 €,0.00 €,"<this> & </that>.""",,,1,<a test&>'
}

function test_13_locally_list_2_payments
{
    local test_name test_output uuid_hex
    test_name="test_13_locally_list_2_payments"
    test_output="$(capture_admin_cgi_output "${test_name}" GET list_payments.cgi "")"
    uuid_hex="$(sql_query 'select uuid from reservations where name="realperson" limit 1')"
    if [ -z "$uuid_hex" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    assert_html_response "$test_name" "$test_output" \
                         '<input type="hidden" id="csrf_token" name="csrf_token" value="'"$csrf_token"'">' \
                         '<input type="file" id="csv_file" name="csv_file">' \
                         '<tr><td>src_id_0</td><td>01/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>3.50</td><td><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex"'">Réservation</a></td></tr>' \
                         '<tr><td>src_id_1</td><td>02/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>69.50</td><td><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex"'">Réservation</a></td></tr>'
}

function test_14_locally_upload_payments
{
    local test_name test_output uuid_hex content_type content_stdin row_count
    test_name="test_14_locally_upload_payments"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    fake_csv="Nº de séquence;Date d'exécution;Date valeur;Montant;Devise du compte;Numéro de compte;Type de transaction;Contrepartie;Nom de la contrepartie;Communication;Détails;Statut;Motif du refus\\n2023-00127;28/03/2023;28/03/2023;18;EUR;BE00010001000101;Virement en euros;BE00020002000202;ccccc-ccccccccc;Reprise marchandises (viande hachee) souper italien;VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISES (VIANDE HACHEE) SOUPER ITALIEN REFERENCE BANQUE : 2303244501612 DATE VALEUR : 28/03/2023;Accepté;\\n"
    eval "$(python3 -c 'import urllib3; body, header = urllib3.encode_multipart_formdata({"csrf_token": "'"$csrf_token"'", "csv_file": ("test.csv", "'"$fake_csv"'"), "submit": "Importer les extraits de compte"}); print(f"content_type={header!r} content_stdin=\"{body.decode('"'utf8'"')}\"")')"
    export CONTENT_STDIN="$content_stdin"
    test_output="$(capture_admin_cgi_output "${test_name}" POST import_payments.cgi "" CONTENT_TYPE="$content_type")"
    export CONTENT_STDIN=""
    grep -q "^Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    target="gestion/list_payments.cgi"
    grep -q "^Location: .*$target" "$test_output" || die "$test_name not redirecting to correct target \`\`$target'' in $test_output"
    if ! row_count="$(count_payments)" ; then
        die "$test_name Could not count payments"
    else
        [ "$row_count" -eq 3 ] || die "$test_name Unexpected row_count=$row_count"
    fi
}

# 01: List reservations when DB is still empty, then
# - Verify output HTML
# - Verify CSRF is in DB
# - Verify reservations is empty
function test_01_list_empty_reservations
{
    local test_output csrf_token
    test_output="$test_dir/01_list_reservations_empty_db.html"
    do_curl_as_admin 'gestion/list_reservations.cgi' "$test_output.tmp"
    csrf_token="$(get_csrf_token_from_html "$test_output.tmp")"
    make_list_reservations_output_deterministic "$test_output.tmp" "$csrf_token" > "$test_output"
    do_diff "$test_output"
    get_db_file
    if [ "$(count_reservations)" != "0" ]; then
        die "Reservations table is not empty."
    fi
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    echo "test_01_list_empty_reservations: ok"
}

# 02: Attempt to register for an invalid date
# - Verify output HTML
# - Verify reservations is still empty
# - No new CSRF token
function test_02_invalid_date_for_reservation
{
    local test_output
    test_output="$test_dir/02_invalid_date_for_reservation.html"
    do_curl 'post_reservation.cgi' "$test_output" "-X POST -F name=TestName02 -F email=Test.Email@example.com -F places=4 -F date=1234-56-78 -F gdpr_accepts_use=1"
    do_diff "$test_output"
    get_db_file
    if [ "$(count_reservations)" != "0" ]; then
        die "test_02_invalid_date_for_reservation: Reservations table is not empty."
    fi
    if [ "$(count_csrfs)" -gt "1" ]; then
        die "test_02_invalid_date_for_reservation: CSRF problem: new CSRF token created."
    fi
    echo "test_02_invalid_date_for_reservation: ok"
}

# 03: Register for a test date
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_03_valid_reservation_for_test_date
{
    generic_test_valid_reservation_for_test_date 03_valid_reservation_for_test_date \
                                                 TestName03 Test.Email@example.com \
                                                 3 2099-01-01 2 0 0 2 1 1 1 1 1
}

# 04: Register for Saturday
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_04_valid_reservation_for_saturday
{
    generic_test_valid_reservation_for_test_date 04_valid_reservation_for_saturday \
                                                 Saturday04 Saturday@gmail.com \
                                                 5 2022-03-19 3 2 0 0 0 0 0 0 2
}

# 05: Register for Sunday: not possible, so Saturday, too...
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_05_valid_reservation_for_sunday
{
    generic_test_valid_reservation_for_test_date 05_valid_reservation_for_sunday \
                                                 Sunday05 SundayMail@gmx.com \
                                                 2 2022-03-19 0 0 0 0 0 0 1 0 3
}

# 06: List reservations with new content, limit & sorting options
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_06_list_reservations
{
    local test_output csrf_token
    test_output="$test_dir/06_list_reservations.html"
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=7&offset=1&sort_order=date&sort_order=name' "$test_output.tmp"
    csrf_token="$(get_csrf_token_from_html "$test_output.tmp")"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    make_list_reservations_output_deterministic "$test_output.tmp" "$csrf_token" > "$test_output"
    do_diff "$test_output"
    echo "test_06_list_reservations: ok"
}

# 07: Admin tries to create new reservation without CSRF token
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_07_new_reservation_without_CSRF_token_fails
{
    generic_test_new_reservation_without_valid_CSRF_token_fails 07_new_reservation_without_CSRF_token_fails ""
}

# 08: Admin tries to create new reservation with wrong CSRF token
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_08_new_reservation_with_wrong_CSRF_token_fails
{
    generic_test_new_reservation_without_valid_CSRF_token_fails 08_new_reservation_without_CSRF_token_fails "-F csrf_token=deadbeefc0ffeeb01"
}

# 09: Admin creates new reservation with correct CSRF token
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
# - Verify new data created
function test_09_new_reservation_with_correct_CSRF_token_succeeds
{
    local test_output csrf_token
    test_output="$test_dir/09_new_reservation_with_correct_CSRF_token_succeeds.html"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    do_curl_with_redirect --admin \
                          'gestion/add_unchecked_reservation.cgi' \
                          "$test_output" \
                          "-X POST -F name=TestCreatedByAdmin -F comment=ByAdmin -F places=8 -F date=2099-01-01 -F outside_fondus=1 -F outside_assiettes=2 -F outside_bolo=4 -F outside_scampis=8 -F outside_tiramisu=4 -F outside_tranches=4 -F csrf_token=$csrf_token"
    get_db_file
    if [ "$(count_csrfs)" -gt "1" ]; then
        die ": CSRF problem: new CSRF token created."
    fi
    if [ "$(count_reservations)" != "4" ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: Reservations table should contain $total_reservations_count row."
    fi
    if [ "$(sql_query "SELECT name, email, places, date, outside_fondus, outside_assiettes, outside_bolo, outside_scampis, outside_tiramisu, outside_tranches, gdpr_accepts_use, active FROM reservations ORDER BY time DESC LIMIT 1;")" \
             != "TestCreatedByAdmin|ByAdmin|8|2099-01-01|1|2|4|8|4|4|0|1" \
       ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: Wrong data saved in DB"
    fi
    do_diff "$test_output"
    echo "test_09_new_reservation_with_correct_CSRF_token_succeeds: ok"
}

# 10: Admin exports data in CSV format
# - Verify output CSV
function test_10_export_as_csv
{
    local test_output substitutions
    test_output="$test_dir/10_export_as_csv.csv"
    do_curl_as_admin 'gestion/export_csv.cgi' "$test_output.tmp"
    tr -d '\r' < "$test_output.tmp" | sed -e "s/,$admin_user\$/,TEST_ADMIN/" > "$test_output"
    do_diff "$test_output"
    echo "test_10_export_as_csv: ok"
}

# 11: Deactivate first reservation to check it does not show up in the list anymore
function test_11_deactivate_a_reservation
{
    local test_output csrf_token
    sql_query 'UPDATE reservations SET active=0 WHERE uuid = (
                   SELECT uuid FROM reservations ORDER BY time ASC LIMIT 1)'
    put_db_file
    test_output="$test_dir/11_deactivate_a_reservation.html"
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=17&sort_order=BOLO&sort_order=name' "$test_output.tmp"
    make_list_reservations_output_deterministic "$test_output.tmp" "$(get_csrf_token_of_user "$admin_user")" > "$test_output"
    do_diff "$test_output"
    echo "test_11_deactivate_a_reservation: ok"
}

# 12: Register with a name with special characters to test HTML escaping & SQL injection resistence
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
# - Verify updated administrative list
function test_12_bobby_tables_and_co
{
    local reservation_name reservation_email sql_output test_output csrf_token
    reservation_name="$test_dir/12_input_name"
    reservation_email="$test_dir/12_input_email"
    sql_output="$test_dir/12_sqlite3_output"
    test_output="$test_dir/12_list_reservations.html"
    # Have curl(1) read the value of some fields from temporary file to be able to
    # pass special characters that my shell quoting skills can't handle:
    echo '"; drop table reservations; select count(1) from csrfs where "2"<"' > "$reservation_name"
    echo '</body></html><!--@example.com' > "$reservation_email"
    generic_test_valid_reservation_for_test_date 12_bobby_tables_and_co \
                                                 "<$reservation_name" \
                                                 "<$reservation_email" \
                                                 3 2022-03-19 1 0 0 2 0 1 2 1 5
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=9' "$test_output.tmp"
    csrf_token="$(get_csrf_token_from_html "$test_output.tmp")"
    get_db_file
    sql_query 'select email,name from reservations where email like "%body%html%"' \
              > "$sql_output"
    do_diff "$sql_output"
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    make_list_reservations_output_deterministic "$test_output.tmp" "$csrf_token" > "$test_output"
    do_diff "$test_output"
    echo "test_12_bobby_tables_and_co: ok"
}

# 13: Try to display a reservation with insufficient or wrong input data to identify it
# Must redirect to concert page
function test_13_show_reservation_redirects_to_concert_page_on_error
{
    local valid_uuid other_valid_uuid test_output test_stderr
    valid_uuid="$(sql_query 'select uuid from reservations limit 1')"
    test_output="$test_dir/13_show_reservation_redirects_to_concert_page_on_error.html"
    test_stderr="$test_dir/13_show_reservation_redirects_to_concert_page_on_error.stderr.log"
    do_curl 'show_reservation.cgi' "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page_for_integration_test "$test_stderr"
    do_curl 'show_reservation.cgi?uuid_hex=invalid_uuid' "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page_for_integration_test "$test_stderr"
    do_curl "show_reservation.cgi?uuid_hex=$valid_uuid" "$test_output" --verbose 2> "$test_stderr"
    grep -q '^< HTTP/1.1 200' "$test_stderr" \
         || die "Failed to get show_reservation.cgi?uuid_hex=$valid_uuid"
    echo "test_13_show_reservation_redirects_to_concert_page_on_error: ok"
}

# 14: Admin tries to generate tickets without CSRF token
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_14_generate_tickets_without_CSRF_token_fails
{
    generic_test_generate_tickets_without_valid_CSRF_token_fails 14_generate_tickets_without_CSRF_token_fails ""
}

# 15: Admin tries to create generate tickets with wrong CSRF token
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_15_generate_tickets_with_wrong_CSRF_token_fails
{
    generic_test_generate_tickets_without_valid_CSRF_token_fails 15_generate_tickets_without_CSRF_token_fails "-F csrf_token=deadbeefc0ffeeb01"
}

function test_16_generate_tickets_with_correct_CSRF_token_succeeds
{
    local csrf_token test_output
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    test_output="$test_dir/16_generate_tickets.html"
    do_curl_as_admin 'gestion/generate_tickets.cgi' \
                     "$test_output" \
                     "-X POST -F fondus=20 -F assiettes=20 -F bolo=20 -F scampis=20 -F tiramisu=20 -F tranches=20 -F csrf_token=$csrf_token"
    do_diff "$test_output"
    echo "test_16_generate_tickets_with_correct_CSRF_token_succeeds: ok"
}

# 17: Get input form to setup ticket generation
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_17_generate_tickets_form_input
{
    local test_output csrf_token
    test_output="$test_dir/17_generate_tickets_form_input.html"
    do_curl_as_admin 'gestion/generate_tickets.cgi' "$test_output.tmp"
    csrf_token="$(sed -n -e 's/.*csrf_token"[^<>]*value="\([a-f0-9A-F]*\)".*/\1/p' "$test_output.tmp")"
    get_db_file
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    sed -e 's/csrf_token" value="'"$csrf_token"'"/csrf_token" value="CSRF_TOKEN"/g' "$test_output.tmp" > "$test_output"
    do_diff "$test_output"
    echo "test_17_generate_tickets_form_input: ok"
}

# First run local unit tests to avoid deploying if it's already broken
(cd "$(dirname "$0")" && python3 -m unittest discover) || die "Unit tests failed"

# Temporary dir to store test outputs and also used as deployment directory name
test_dir="$(mktemp --directory)"
folder="$(basename "$test_dir")"
db_file="$test_dir/db.db"

cat <<EOF
Storing test output in '$test_dir', clean with
    rm -r '$test_dir';
EOF

if [ -n "$dash_x" ];
then
    set -x
fi

test_01_locally_valid_post_reservation
test_02_locally_invalid_show_reservation
test_03_locally_display_existing_reservation
test_04_locally_invalid_post_reservation
test_05_locally_list_reservations
test_06_locally_add_unchecked_reservation_CSRF_failure
test_07_locally_add_unchecked_reservation
test_08_locally_GET_generate_tickets
test_09_locally_POST_generate_tickets
test_10_locally_list_payments_before_adding_any_to_db
test_11_locally_reservation_example
test_12_locally_export_csv
test_13_locally_list_2_payments
test_14_locally_upload_payments

# Temporarily disable command logging for deployment
set +x

if [ -n "$skip_deploy" ];
then
    echo "Everything is fine so far.  Skipping tests requiring deployment"
    exit 0
fi

ssh_app_folder="$host_path_prefix/$folder"
cat <<EOF
Deploying to '$ssh_app_folder', clean with
    ssh '$destination' "rm -r '$ssh_app_folder'";
EOF

# Deploy
"$(dirname "$0")/../deploy.sh" "--for-tests" "$destination" "$user" "$group" "$ssh_app_folder" "$admin_user" "$admin_pw"
echo '{ "paying_seat_cents": 500, "bank_account": "'$bank_account'", "info_email": "'$info_email'" }' \
    | ssh "$destination" \
          "touch '$ssh_app_folder/configuration.json'; cat > '$ssh_app_folder/configuration.json'"

# tests are flaky: sometimes the first curl call returns an empty document.
sleep 1
do_curl_as_admin 'gestion/list_reservations.cgi' "$test_dir/dummy_fetch.html"


if [ -n "$dash_x" ];
then
    set -x
fi

# Tests
test_01_list_empty_reservations
test_02_invalid_date_for_reservation
test_03_valid_reservation_for_test_date
test_04_valid_reservation_for_saturday
test_05_valid_reservation_for_sunday
test_06_list_reservations
test_07_new_reservation_without_CSRF_token_fails
test_08_new_reservation_with_wrong_CSRF_token_fails
test_09_new_reservation_with_correct_CSRF_token_succeeds
test_10_export_as_csv
test_11_deactivate_a_reservation
test_12_bobby_tables_and_co
test_13_show_reservation_redirects_to_concert_page_on_error
test_14_generate_tickets_without_CSRF_token_fails
test_15_generate_tickets_with_wrong_CSRF_token_fails
test_16_generate_tickets_with_correct_CSRF_token_succeeds
test_17_generate_tickets_form_input

# Clean up
ssh $destination "rm -r '$host_path_prefix/$folder'"
rm -r "$test_dir"

echo Done

# Local Variables:
# compile-command: "time ./tests.sh -x -f"
# End:
