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

if [ -z "$host_path_prefix" -o -z "$base_url" ];
then
    echo "Missing parameters: '$0'$dash_x '$base_url' '$host_path_prefix' '$destination' '$user' '$group' '$admin_user' '$admin_pw'"
    echo "Usage: $(basename "$0") [-x] <base-url> <host-path-prefix> <ssh-host> <user> <group> [<admin-user> <admin-pw>]"
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
    curl --silent "$end_point" $3 \
        | sed -e "s;$folder;TEST_DIR;g" -e "s;$base_url;TEST_HOST;g" -e "s;mailto:$info_email;TEST_EMAIL;g"\
              > "$2"
}

function do_curl {
    _do_curl "$1" "$2" "$3"
}

function do_curl_as_admin {
    _do_curl "$1" "$2" "$3" "$admin_user:$admin_pw@"
}

function assert_redirect_to_concert_page
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
    location="$(sed -n -e 's/^< Location: *//p' "$test_stderr")"
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
    local test_name spectator_name spectator_email places concert_date outside_fondus outside_assiettes outside_bolo outside_scampis outside_tiramisu outside_tranches inside_assiettes_bolo_tiramisu gdpr_accepts_use total_reservations_count test_output communication formatted_communication
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
    assert_redirect_to_concert_page "$test_stderr"
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
    assert_redirect_to_concert_page "$test_stderr"
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

# Test definitions

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
    local test_output csrf_token communication
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
    sed -e "s/,$admin_user,/,TEST_ADMIN,/" "$test_output.tmp" > "$test_output"
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
    assert_redirect_to_concert_page "$test_stderr"
    do_curl 'show_reservation.cgi?uuid_hex=invalid_uuid' "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page "$test_stderr"
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
(cd "$(dirname "$0")" && python -m unittest discover) || die "Unit tests failed"

# Temporary dir to store test outputs and also used as deployment directory name
test_dir="$(mktemp --directory)"
folder="$(basename "$test_dir")"
ssh_app_folder="$host_path_prefix/$folder"
db_file="$test_dir/db.db"

cat <<EOF
Storing test output in '$test_dir', clean with
    rm -r '$test_dir';
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
