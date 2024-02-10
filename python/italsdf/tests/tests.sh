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
venv_abs_path="$(or_default "$6" "$host_path_prefix/venv_$pseudo_random")"
admin_user="$(or_default "$7" "user_$pseudo_random")"
admin_pw="$(or_default "$8" "pw_$pseudo_random")"
bank_account="BExx-$pseudo_random"
info_email="mrx.$pseudo_random@example.com"

if [ -z "$skip_deploy" -a '(' -z "$host_path_prefix" -o -z "$base_url" -o -z "$destination" -o -z "$user" -o -z "$group" ')' ];
then
    echo "Missing parameters: '$0'$dash_x$skip_deploy '$base_url' '$host_path_prefix' '$destination' '$user' '$group' '$venv_abs_path' '$admin_user' '$admin_pw'"
    echo "Usage: $(basename "$0") [-x] [-f] <base-url> <host-path-prefix> <ssh-host> <user> <group> [<venv-abs-path> [<admin-user> [<admin-pw>]]]"
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
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr" || die "No 302 status code found in $test_stderr"
    location="$(tr -d '\r' < "$test_stderr" | sed -n -e 's/^< Location: *//p')"
    do_curl "$location" "$test_output"
}

function die {
    >&2 echo $1
    exit 2
}

function get_db_file {
    scp "$destination:$ssh_app_folder/db.db" "$db_file"
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

function get_bank_id_from_reservation_uuid {
    sql_query "SELECT bank_id FROM reservations WHERE uuid='$1';" \
        | sed -e 's;\(...\)\(....\)\(.....\);+++\1/\2/\3+++;'
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
    local test_name spectator_name spectator_email places concert_date outside_extra_starter outside_main_starter outside_main_dish outside_extra_dish outside_main_dessert outside_extra_dessert inside_main_starter_main_dish_main_dessert gdpr_accepts_use total_reservations_count test_output
    test_name="$1"
    spectator_name="$2"
    spectator_email="$3"
    places="$4"
    concert_date="$5"
    outside_extra_starter="$6"
    outside_main_starter="$7"
    outside_main_dish="$8"
    outside_extra_dish="$9"; shift
    outside_main_dessert="$9"; shift
    outside_extra_dessert="$9"; shift
    inside_main_starter_main_dish_main_dessert="$9"; shift
    gdpr_accepts_use="$9"; shift
    total_reservations_count="$9"
    test_output="$test_dir/$test_name.html"
    do_curl_with_redirect 'post_reservation.cgi' \
                          "$test_output" \
                          "-X POST -F name=$spectator_name -F email=$spectator_email -F places=$places -F date=$concert_date -F outsideextrastarter=$outside_extra_starter -F outsidemainstarter=$outside_main_starter -F outsidemaindish=$outside_main_dish -F outsideextradish=$outside_extra_dish -F outsidemaindessert=$outside_main_dessert -F outsideextradessert=$outside_extra_dessert -F insidemainstarter=$inside_main_starter_main_dish_main_dessert -F insidemaindish=$inside_main_starter_main_dish_main_dessert -F insidemaindessert=$inside_main_starter_main_dish_main_dessert -F gdpr_accepts_use=$gdpr_accepts_use"
    grep --quiet --fixed --regexp="$spectator_name" "$test_output" || die "No \`\`$spectator_name'' in $test_output"
    get_db_file
    if [ "$(count_reservations)" != "$total_reservations_count" ]; then
        die "test_$test_name: Reservations table should contain $total_reservations_count row."
    fi
    if [ "$(sql_query "SELECT name, email, places, date, outside_extra_starter, outside_main_starter, outside_main_dish, outside_extra_dish, outside_main_dessert, outside_extra_dessert, inside_main_starter, inside_main_dish, inside_extra_dish, inside_main_dessert, gdpr_accepts_use, active FROM reservations WHERE name = '$spectator_name' AND email = '$spectator_email' AND places = $places;")" \
             != "$spectator_name|$spectator_email|$places|$concert_date|$outside_extra_starter|$outside_main_starter|$outside_main_dish|$outside_extra_dish|$outside_main_dessert|$outside_extra_dessert|$inside_main_starter_main_dish_main_dessert|$inside_main_starter_main_dish_main_dessert|0|$inside_main_starter_main_dish_main_dessert|$gdpr_accepts_use|1" \
       ]; then
        die "test_$test_name: Wrong data saved in DB"
    fi
    if [ "$(count_csrfs)" -gt "1" ]; then
        die "test_$test_name: CSRF problem: new CSRF token created."
    fi
    echo "test_$test_name: ok"
}

function get_csrf_token_from_html
{
    sed -n -e 's/.*<input type="hidden" name="csrf_token" value="\([a-f0-9A-F]*\)">.*/\1/p' "$1"
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
        sed -e 's/value="'"$csrf_token"'"/value="CSRF_TOKEN"/g' \
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
    echo "${CONTENT_STDIN:-}" | (
        cd "$app_dir/$(dirname "$script_name")" \
            && env TEMP="$test_dir" \
                   REQUEST_METHOD="$method" \
                   QUERY_STRING="$query_string" \
                   SERVER_NAME=example.com \
                   SCRIPT_NAME="/$script_name" \
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
        grep -q '</title><link rel="stylesheet" href="styles.css"><link rel="stylesheet"[^>]*bootstrap[^>]*></head><body><div id="branding" role="banner"><h1 id="site-title">Société Royale d'\''Harmonie de Braine-l'\''Alleud</h1><img src="https://www.srhbraine.be/wp-content/uploads/2019/10/site-en-tete.jpg" width="940" height="198" alt=""></div>' "$test_output" || die "$test_name no banner in $test_output"
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
    local test_name test_output uuid_hex data expected_data
    test_name="test_01_locally_valid_post_reservation"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi 'name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidemaindish=4&insideextradish=1&insidethirddish=2&kidsmaindish=8&kidsextradish=5&kidsthirddish=4&outsidemainstarter=10&outsideextrastarter=11&outsidemaindish=12&outsideextradish=13&outsidemaindessert=14&outsideextradessert=15&kidsmaindessert=2&kidsextradessert=15&insidemaindessert=3&insideextradessert=4&gdpr_accepts_use=true&date=2099-01-01')"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        [ "$(count_reservations)" = 1 ] || die "$test_name: Reservation count"
        data=$(sql_query "SELECT name, email, extra_comment, date, places, inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert, outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_main_dessert, outside_extra_dessert, kids_main_dish, kids_extra_dish, kids_third_dish, kids_main_dessert, kids_extra_dessert FROM reservations WHERE uuid='$uuid_hex'")
        expected_data="test|i@example.com|commentaire|2099-01-01|1|2|5|4|1|2|3|4|10|11|12|13|14|15|8|5|4|2|15"
        [ "$data" = "$expected_data" ] || die "$test_name Wrong data inserted for $uuid_hex: '$data' instead of '$expected_data'"
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
    sql_query 'INSERT INTO reservations VALUES ("<name>", "email@domain.com", "<this> & </that>'\''""", 2, "2099-01-01", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, "", "'"$test_name"'", "'$(date +"%s")'", 1, "<a test&>")'
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

    inside_menu_mismatch_query_string='name=test&email=i%40example.com&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidemaindish=0&insideextradish=3&kidsmaindish=8&kidsextradish=9&outsidemainstarter=10&outsideextrastarter=11&outsidemaindish=12&outsideextradish=13&outsidemaindessert=14&gdpr_accepts_use=true&date=2099-01-01'
    query_string="$inside_menu_mismatch_query_string"
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi "$query_string")"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        die "$test_name reservation $uuid_hex created for invalid $query_string"
    fi
    assert_html_response "$test_name" "$test_output" \
                         "invalides dans le formulaire" \
                         "ne correspond pas au nombre de plats"

    invalid_email_query_string='name=test&email=example.com%40&extraComment=commentaire&places=1&insidemainstarter=2&insideextrastarter=5&insidemaindish=4&insideextradish=3&kidsmaindish=8&kidsextradish=9&outsidemainstarter=10&outsideextrastarter=11&outsidemaindish=12&outsideextradish=13&outsidemaindessert=14&gdpr_accepts_use=true&date=2099-01-01'
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
    local test_name test_output uuid_hex bank_transaction_number csrf_token
    test_name="test_05_locally_list_reservations"
    test_output="$(capture_admin_cgi_output "$test_name" GET list_reservations.cgi "")"
    # Check that the output contains a link to the payment info and the transaction number
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    uuid_hex="$(sql_query 'select uuid from reservations limit 1')"
    bank_transaction_number="$(get_bank_id_from_reservation_uuid "$uuid_hex")"
    assert_html_response "$test_name" "$test_output" \
                         "https://example.com/gestion/list_reservations\\.cgi" \
                         "<li>12 Tomates Mozzarella</li>" \
                         "<li>16 Croquettes au fromage</li>" \
                         "<li>16 Spaghettis bolognaise</li>" \
                         "<li>2 Spaghettis aux légumes</li>" \
                         "<li>8 Spag\\. bolognaise (enfants)</li>" \
                         "<li>4 Spag\\. aux légumes (enfants)</li>" \
                         "<li>19 Fondus au chocolat</li>" \
                         "<li>34 Portions de glace</li>" \
                         "<a href=[^ ]*show_reservation[^ ]*$uuid_hex" \
                         "$bank_transaction_number" \
                         '<li><a href="list_payments.cgi">Gérer les paiements</a></li>' \
                         '<li><a href="generate_tickets.cgi">Générer les tickets nourriture pour impression</a></li>' \
                         "document.addEventListener('DOMContentLoaded', function () {" \
                         '<input type="hidden" name="csrf_token" value="'"$csrf_token"'">'
}

function test_06_locally_add_unchecked_reservation_CSRF_failure
{
    local test_name test_output
    test_name="test_06_locally_add_unchecked_reservation_CSRF_failure"
    test_output="$(capture_admin_cgi_output "$test_name" POST add_unchecked_reservation.cgi 'name=Qui+m%27appelle%3F&extraComment=02%2F123.45.67&places=1&insidemainstarter=1&insideextrastarter=0&insidemaindish=0&insideextradish=1&kidsmaindish=0&kidsextradish=0&outsidemainstarter=0&outsideextrastarter=0&outsidemaindish=0&outsideextradish=0&outsidemaindessert=0&csrf_token=this-is-not-a-valid-CSRF-token&date=2024-03-23')"
    assert_redirect_to_concert_page_for_local_test "$test_name" "$test_output"
}

function test_07_locally_add_unchecked_reservation
{
    local test_name test_output csrf uuid_hex data expected_data
    test_name="test_07_locally_add_unchecked_reservation"
    csrf="$(get_csrf_token_of_user "$admin_user")"
    test_output="$(capture_admin_cgi_output "$test_name" POST add_unchecked_reservation.cgi "name=Qui+m%27appelle%3F&extraComment=02%2F123.45.67&places=1&insidemainstarter=1&insideextrastarter=0&insidemaindish=0&insideextradish=0&insidethirddish=1&kidsmaindish=0&kidsextradish=0&outsidemainstarter=0&outsideextrastarter=0&outsidemaindish=0&outsideextradish=0&outsidethirddessert=0&outsidemaindessert=0&outsideextradessert=0&insideextradessert=1&csrf_token=$csrf&date=2024-03-23")"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        [ "$(count_reservations)" = 3 ] || die "$test_name: Reservation count"
        data=$(sql_query "SELECT name, email, extra_comment, date, places, inside_main_starter, inside_extra_starter, inside_main_dish, inside_extra_dish, inside_third_dish, inside_main_dessert, inside_extra_dessert, outside_main_starter, outside_extra_starter, outside_main_dish, outside_extra_dish, outside_third_dish, outside_main_dessert, outside_extra_dessert, kids_main_dish, kids_extra_dish FROM reservations WHERE uuid='$uuid_hex'")
        expected_data="Qui m'appelle?||02/123.45.67|2024-03-23|1|1|0|0|0|1|0|1|0|0|0|0|0|0|0|0|0"
        [ "$data" = "$expected_data" ] || die "$test_name Wrong data inserted for $uuid_hex: '$data' but wanted '$expected_data'"
    else
        die "$test_name uuid_hex not found in $test_output"
    fi
}

function test_08_locally_GET_generate_tickets
{
    local test_name test_output csrf
    test_name="test_08_locally_GET_generate_tickets"
    test_output="$(capture_admin_cgi_output "$test_name" GET generate_tickets.cgi "")"
    csrf="$(get_csrf_token_of_user "$admin_user")"
    assert_html_response "$test_name" "$test_output" \
                         "Impression des tickets pour la nourriture" \
                         'name="csrf_token" value="'"$csrf"'"' \
                         '<form method="POST"' \
                         'label for="main_starter">.*:</label><input type="number" id="main_starter" name="main_starter"' \
                         'label for="extra_starter">.*:</label><input type="number" id="extra_starter" name="extra_starter"' \
                         'label for="main_dish">.*:</label><input type="number" id="main_dish" name="main_dish"' \
                         'label for="extra_dish">.*:</label><input type="number" id="extra_dish" name="extra_dish"' \
                         'label for="third_dish">.*:</label><input type="number" id="third_dish" name="third_dish"' \
                         'label for="kids_main_dish">.*:</label><input type="number" id="kids_main_dish" name="kids_main_dish"' \
                         'label for="kids_extra_dish">.*:</label><input type="number" id="kids_extra_dish" name="kids_extra_dish"' \
                         'label for="kids_third_dish">.*:</label><input type="number" id="kids_third_dish" name="kids_third_dish"' \
                         'label for="main_dessert">.*:</label><input type="number" id="main_dessert" name="main_dessert"' \
                         'label for="extra_dessert">.*:</label><input type="number" id="extra_dessert" name="extra_dessert"'

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

    csrf="$(get_csrf_token_of_user "$admin_user")"
    test_output="$(capture_admin_cgi_output --ignore-cgitb "${test_name}_only_csrf" POST generate_tickets.cgi "csrf_token=$csrf")"
    grep -q "RuntimeError: Not enough tickets" "$test_output" || die "${test_name}_only_csrf should contain RuntimeError because a lack of tickets"
    test_output="$(capture_admin_cgi_output "${test_name}" POST generate_tickets.cgi "csrf_token=$csrf&main_starter=19&extra_starter=41&main_dish=42&extra_dish=73&third_dish=20&kids_main_dish=74&kids_extra_dish=75&kids_third_dish=28&main_dessert=20&extra_dessert=35")"
    assert_html_response --no-banner "$test_name" "$test_output" \
                         "<title>Liste des tickets à imprimer</title>" \
                         "Qui m'appelle[^:]*: 1 place.*pour 3 tickets: 1m[+0c]* Tomate Mozzarella, 1m[+0c]* Spaghetti aux légumes, 1m[+0c]* Portion de glace" \
                         "test[^:]*: 1 place.*pour 130 tickets: 2m[+]10c Tomate Mozzarella, 5m[+]11c Croquettes au fromage, 4m[+]12c Spaghetti bolognaise, 1m[+]13c Spaghetti aux scampis, 2m[+]0c Spaghetti aux légumes, 8m[+]0c Spag. bolognaise (enfants), 5m[+]0c Spag. aux scampis (enfants), 4m[+]0c Spag. aux légumes (enfants), 5m[+]14c Fondu au chocolat, 19m[+]15c Portion de glace" \
                         "Vente libre</div><div>Tomate Mozzarella=6, Croquettes au fromage=25, Spaghetti bolognaise=26, Spaghetti aux scampis=59, Spaghetti aux légumes=17, Spag. bolognaise (enfants)=66, Spag. aux scampis (enfants)=70, Spag. aux légumes (enfants)=24, Fondu au chocolat=1, Portion de glace=0</div>"
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
    test_output="$(capture_cgi_output "$test_name" POST post_reservation.cgi 'name=realperson&email=i%40gmail.com&extraComment=commentaire&places=2&insidemainstarter=1&insideextrastarter=0&insidemaindish=1&insideextradish=0&insideextradessert=1&kidsmaindish=1&kidsextradish=0&kidsextradessert=1&outsidemainstarter=0&outsideextrastarter=1&outsidemaindish=0&outsideextradish=0&outsideextradessert=0&outsidemaindessert=3&gdpr_accepts_use=false&date=2024-03-23')"
    grep -q "Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    if uuid_hex="$(sed -ne '/Location:.*uuid_hex=/ { s///p ; q0 }' -e '$q1' "$test_output")"; then
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Le prix total est de 68.00 € pour le repas" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">3 Fondus au chocolat</li>" \
                             ">2 Portions de glace</li>" \
                             "Nous vous saurions gré de déjà verser cette somme avec la communication structurée" \
                             "code QR avec votre application bancaire mobile: <br><svg"

        sql_query 'INSERT INTO payments VALUES (NULL, 2.3, 350, "partial payment", "'"$uuid_hex"'", "src_id_0", "BE001100", "realperson", "Accepté", "unit test admin user", "1.2.3.4")'
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Le prix total est de 68.00 € pour le repas dont 64.50 € sont encore dûs" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">3 Fondus au chocolat</li>" \
                             ">2 Portions de glace</li>" \
                             "Nous vous saurions gré de déjà verser cette somme avec la communication structurée" \
                             "code QR avec votre application bancaire mobile: <br><svg"

        sql_query 'INSERT INTO payments VALUES (NULL, 86405.5, 6450, "partial payment", "'"$uuid_hex"'", "src_id_1", "BE001100", "realperson", "Accepté", "unit test admin user", "1.2.3.4")'
        test_output="$(capture_cgi_output "$test_name" GET show_reservation.cgi "uuid_hex=$uuid_hex")"
        assert_html_response "$test_name" "$test_output" \
                             "Merci d'avoir déjà réglé l'entièreté des 68.00 € dûs" \
                             ">1 Tomate Mozzarella</li>" \
                             ">1 Croquettes au fromage</li>" \
                             ">Plat: 1 Spaghetti bolognaise</li>" \
                             ">Plat enfants: 1 Spag. bolognaise (enfants)</li>" \
                             ">3 Fondus au chocolat</li>" \
                             ">2 Portions de glace</li>"
        assert_not_in_html_response "$test_name" "$test_output" "verser cette somme avec la communication structurée" "code QR avec votre application bancaire mobile: <br><svg"
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
                        "realperson,2,1,0,1,0,0,0,1,1,0,0,0,1,0,1,0,0,0,3,0,68.00 €,0.00 €,commentaire,i@gmail.com,,1," \
                        '<name>,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.00 €,0.00 €,"<this> & </that>'"'"'""",,,1,<a test&>'
}

function test_13_locally_list_2_payments
{
    local test_name test_output uuid_hex csrf_token
    test_name="test_13_locally_list_2_payments"
    test_output="$(capture_admin_cgi_output "${test_name}" GET list_payments.cgi "limit=20&sort_order=src_id")"
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
                         '<tr><td>src_id_0</td><td>01/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>3.50</td><td><form method="POST" action="/gestion/link_payment_and_reservation.cgi"><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex"'">realperson i@gmail.com</a> <input type="hidden" name="csrf_token" value="'"$csrf_token"'"><input type="hidden" name="src_id" value="src_id_0"><input type="hidden" name="reservation_uuid" value=""><input type="submit" value="X"></form></td></tr>' \
                         '<tr><td>src_id_1</td><td>02/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>64.50</td><td><form method="POST" action="/gestion/link_payment_and_reservation.cgi"><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex"'">realperson i@gmail.com</a> <input type="hidden" name="csrf_token" value="'"$csrf_token"'"><input type="hidden" name="src_id" value="src_id_1"><input type="hidden" name="reservation_uuid" value=""><input type="submit" value="X"></form></td></tr>'
}

function test_14_locally_upload_payments
{
    local test_name test_output uuid_hex content_boundary row_count bank_transaction_number csrf_token
    test_name="test_14_locally_upload_payments"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    uuid_hex="$(sql_query 'select uuid from reservations where name="test" limit 1')"
    if [ -z "$uuid_hex" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    bank_transaction_number="$(get_bank_id_from_reservation_uuid "$uuid_hex")"
    if [ -z "$bank_transaction_number" ]; then
        die "$test_name Unable to find bank transaction number"
    fi
    content_boundary='95173680fbda20e37a8df066f0d77cc4'
    export CONTENT_STDIN="--${content_boundary}
Content-Disposition: form-data; name=\"csrf_token\"

$csrf_token
--${content_boundary}
Content-Disposition: form-data; name=\"csv_file\"; filename=\"test.csv\"
Content-Type: text/csv

Nº de séquence;Date d'exécution;Date valeur;Montant;Devise du compte;Numéro de compte;Type de transaction;Contrepartie;Nom de la contrepartie;Communication;Détails;Statut;Motif du refus
2023-00127;28/03/2023;28/03/2023;18;EUR;BE00010001000101;Virement en euros;BE00020002000202;ccccc-ccccccccc;reprise marchandise;VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISE REFERENCE BANQUE : 2303244501612 DATE VALEUR : 28/03/2023;Accepté;
2023-00119;25/03/2023;24/03/2023;27;EUR;BE00010001000101;Virement instantané en euros;BE100010001010;SSSSSS GGGGGGGG;${bank_transaction_number};VIREMENT INSTANTANE EN EUROS BE10 0010 0010 10 BIC GABBBEBBXXX SSSSSS GGGGGGGG RUE MARIGNON 43/5 8888 BANDARLOG COMMUNICATION : xxx EXECUTE LE 24/03 REFERENCE BANQUE : 2303244502842 DATE VALEUR : 24/03/2023;Accepté;


--${content_boundary}
Content-Disposition: form-data; name=\"submit\"

Importer les extraits de compte
--${content_boundary}--
"
    test_output="$(capture_admin_cgi_output "${test_name}" POST import_payments.cgi "" CONTENT_TYPE="multipart/form-data; boundary=$content_boundary")"
    export CONTENT_STDIN=""
    grep -q "^Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    target="gestion/list_payments.cgi"
    grep -q "^Location: .*$target" "$test_output" || die "$test_name not redirecting to correct target \`\`$target'' in $test_output"
    if ! row_count="$(count_payments)" ; then
        die "$test_name Could not count payments"
    else
        [ "$row_count" -eq 4 ] || die "$test_name Unexpected row_count=$row_count"
    fi
}

function test_15_locally_list_4_payments
{
    local test_name test_output uuid_hex_p1_and_p2 uuid_hex_p4 csrf_token
    test_name="test_15_locally_list_4_payments"
    test_output="$(capture_admin_cgi_output "${test_name}" GET list_payments.cgi "limit=20")"
    uuid_hex_p1_and_p2="$(sql_query 'select uuid from reservations where name="realperson" limit 1')"
    if [ -z "$uuid_hex_p1_and_p2" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    uuid_hex_p4="$(sql_query 'select uuid from reservations where name="test" limit 1')"
    if [ -z "$uuid_hex_p4" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    assert_html_response "$test_name" "$test_output" \
                         '<input type="hidden" id="csrf_token" name="csrf_token" value="'"$csrf_token"'">' \
                         '<input type="file" id="csv_file" name="csv_file">' \
                         '<tr><td>src_id_0</td><td>01/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>3.50</td><td><form method="POST" action="/gestion/link_payment_and_reservation.cgi"><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex_p1_and_p2"'">realperson i@gmail.com</a> <input type="hidden" name="csrf_token" value="'"$csrf_token"'"><input type="hidden" name="src_id" value="src_id_0"><input type="hidden" name="reservation_uuid" value=""><input type="submit" value="X"></form></td></tr>' \
                         '<tr><td>src_id_1</td><td>02/01/1970</td><td>BE001100</td><td>realperson</td><td>Accepté</td><td>partial payment</td><td>64.50</td><td><form method="POST" action="/gestion/link_payment_and_reservation.cgi"><a href="https://example.com/show_reservation.cgi?uuid_hex='"$uuid_hex_p1_and_p2"'">realperson i@gmail.com</a> <input type="hidden" name="csrf_token" value="'"$csrf_token"'"><input type="hidden" name="src_id" value="src_id_1"><input type="hidden" name="reservation_uuid" value=""><input type="submit" value="X"></form></td></tr>' \
                         "<tr><td>2023-00127</td><td>28/03/2023</td><td>BE00020002000202</td><td>ccccc-ccccccccc</td><td>Accepté</td><td>reprise marchandise</td><td>18.00</td><td><form method=\"POST\" action=\"/gestion/link_payment_and_reservation.cgi\"><input type=\"hidden\" name=\"csrf_token\" value=\"$csrf_token\"><input type=\"hidden\" name=\"src_id\" value=\"2023-00127\"><select name=\"reservation_uuid\"><option value=\"\">--- Choisir la réservation correspondante ---</option>.*</select>.*</form></td></tr><tr><td>2023-00119</td>" \
                         "<tr><td>2023-00119</td><td>25/03/2023</td><td>BE100010001010</td><td>SSSSSS GGGGGGGG</td><td>Accepté</td><td>[0-9+/]*</td><td>27.00</td><td><form method=\"POST\" action=\"/gestion/link_payment_and_reservation.cgi\"><input type=\"hidden\" name=\"csrf_token\" value=\"$csrf_token\"><input type=\"hidden\" name=\"src_id\" value=\"2023-00119\"><select name=\"reservation_uuid\"><option value=\"$uuid_hex_p4\" selected=\"selected\">[0-9+/]* test i@example.com</option><option value"
}

function test_16_link_payment_and_reservation
{
    local test_name test_output uuid_hex_p4 csrf_token content_boundary payment_uuid src_id
    test_name="test_16_link_payment_and_reservation"
    src_id="2023-00119"
    uuid_hex_p4="$(sql_query 'select uuid from reservations where name="test" limit 1')"
    if [ -z "$uuid_hex_p4" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    content_boundary='95173680fbda20e37a8df066f0d77cc4'
    export CONTENT_STDIN="--${content_boundary}
Content-Disposition: form-data; name=\"csrf_token\"

$csrf_token
--${content_boundary}
Content-Disposition: form-data; name=\"reservation_uuid\"

$uuid_hex_p4
--${content_boundary}
Content-Disposition: form-data; name=\"src_id\"

$src_id
--${content_boundary}--
"
    test_output="$(capture_admin_cgi_output "${test_name}" POST link_payment_and_reservation.cgi '' CONTENT_TYPE="multipart/form-data; boundary=$content_boundary")"
    export CONTENT_STDIN=""
    grep -q "^Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    target="/gestion/list_payments.cgi"
    grep -q "^Location: .*$target" "$test_output" || die "$test_name not redirecting to correct target \`\`$target'' in $test_output"
    payment_uuid="$(sql_query 'select uuid from payments where src_id="'"$src_id"'" limit 1')"
    [ "$payment_uuid" == "$uuid_hex_p4" ] || die "$test_name payment.uuid='$payment_uuid' not linked with reservation '$uuid_hex_p4'"
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

# 02: Register for a test date
# - Verify output HTML very lightly
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_02_valid_reservation_for_test_date
{
    generic_test_valid_reservation_for_test_date 02_valid_reservation_for_test_date \
                                                 TestName03 Test.Email@example.com \
                                                 3 2099-01-01 2 0 0 2 1 1 1 1 1
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
test_15_locally_list_4_payments
test_16_link_payment_and_reservation

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
    ssh '$destination' "rm -r '$ssh_app_folder' '$venv_abs_path'";
EOF

# Deploy
"$(dirname "$0")/../deploy.sh" "--for-tests" "$destination" "$user" "$group" "$base_url" "$host_path_prefix" "$folder" "$venv_abs_path" "$admin_user" "$admin_pw"
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
test_02_valid_reservation_for_test_date

# Clean up
ssh $destination "rm -r '$host_path_prefix/$folder' '$venv_abs_path'"
rm -r "$test_dir"

echo Done

# Local Variables:
# compile-command: "time ./tests.sh -x -f"
# End:
