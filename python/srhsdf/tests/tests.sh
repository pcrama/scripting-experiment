#!/bin/sh

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
admin_user="$(or_default "$6" test_admin)"
admin_pw="$(or_default "$7" test_password)"

if [ -z "$host_path_prefix" -o -z "$base_url" ];
then
    echo "Missing parameters: '$0'$dash_x '$base_url' '$host_path_prefix' '$destination' '$user' '$group' '$admin_user' '$admin_pw'"
    echo "Usage: $(basename "$0") [-x] <base-url> <host-path-prefix> <ssh-host> <user> <group> [<admin-user> <admin-pw>]"
    exit 1
fi

# Where 'golden' reference files are stored
golden="$(dirname "$0")/golden"

# Temporary dir to store test outputs and also used as deployment directory name
test_dir="$(mktemp --directory)"
folder="$(basename "$test_dir")"
ssh_app_folder="$host_path_prefix/$folder"
db_file="$test_dir/db.db"

cat <<EOF
Storing test output in '$test_dir', clean with
    rm -r '$test_dir'
Deploying to '$ssh_app_folder', clean with
    ssh '$destination' "rm -r '$ssh_app_folder'"
EOF

# Make web request
# - $1: end point
# - $2: output file
# - $3: curl options
# - $4: credentials
function _do_curl {
    curl --silent "https://$4$base_url/$folder/$1" $3 \
        | sed -e "s/$folder/TEST_DIR/g" \
              > "$2"
}

function do_curl {
    _do_curl "$1" "$2" "$3"
}

function do_curl_as_admin {
    _do_curl "$1" "$2" "$3" "$admin_user:$admin_pw@"
}

function die {
    echo $1
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

function get_user_of_csrf_token {
    sql_query "SELECT user FROM csrfs WHERE token='$1';"
}

function get_csrf_token_of_user {
    # Ignores IP address... but there should be only one anyway.
    sql_query "SELECT token FROM csrfs WHERE user='$1' ORDER BY timestamp DESC LIMIT 1;"
}

function do_diff {
    reference="$golden/$(basename "$test_output")"
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
    test_name="$1"
    spectator_name="$2"
    spectator_email="$3"
    concert_date="$4"
    paying_seats="$5"
    free_seats="$6"
    cents_due="$7"
    gdpr_accepts_use="$8"
    total_reservations_count="$9"
    test_output="$test_dir/$test_name.html"
    do_curl 'post_reservation.cgi' "$test_output.tmp" "-X POST -F name=$spectator_name -F email=$spectator_email -F date=$concert_date -F paying_seats=$paying_seats -F free_seats=$free_seats -F gdpr_accepts_use=$gdpr_accepts_use"
    communication="$(sed -n -e 's;.*<code>+++\([0-9][0-9][0-9]\)/\([0-9][0-9][0-9][0-9]\)/\([0-9][0-9][0-9][0-9][0-9]\)+++</code>.*;\1\2\3;p' "$test_output.tmp")"
    formatted_communication="$(sed -n -e 's;.*<code>\(+++[0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9][0-9]+++\)</code>.*;\1;p' "$test_output.tmp")"
    if [ -z "$communication" ]; then
       die "test_$test_name: no bank ID"
    fi
    sed -e "s;$formatted_communication;COMMUNICATION;g" "$test_output.tmp" > "$test_output"
    do_diff "$test_output"
    get_db_file
    if [ "$(count_reservations)" != "$total_reservations_count" ]; then
        die "test_$test_name: Reservations table should contain $total_reservations_count row."
    fi
    if [ "$(sql_query "SELECT name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, active, bank_id FROM reservations WHERE bank_id = '$communication';")" \
             != "$spectator_name|$spectator_email|$concert_date|$paying_seats|$free_seats|$gdpr_accepts_use|$cents_due|1|$communication" \
       ]; then
        die "test_$test_name: Wrong data saved in DB"
    fi
    if [ "$(count_csrfs)" != "1" ]; then
        die "test_$test_name: CSRF problem: new CSRF token created."
    fi
    echo "test_$test_name: ok"
}

function generic_test_new_reservation_without_valid_CSRF_token_fails
{
    test_name="$1"
    csrf_arg="$2"
    test_output="$test_dir/$test_name.will-be-empty"
    test_stderr="$test_dir/$test_name.stderr.log"
    do_curl_as_admin 'gestion/add_unchecked_reservation.cgi' \
                     "$test_output" \
                     "-X POST -F name=$test_name -F email=ByAdminNoCsrf@email.com -F date=2099-01-01 -F paying_seats=3 -F free_seats=5 $csrf_arg --verbose" \
                     2> "$test_stderr"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    if [ "$(count_csrfs)" != "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr"
    grep -q '^< Content-Length: 0' "$test_stderr"
    grep -q '^< Location: https://www.srhbraine.be/concert-de-gala-2021/' "$test_stderr"
    echo "test_$test_name: ok"
}

# Test definitions

# 01: List reservations when DB is still empty, then
# - Verify output HTML
# - Verify CSRF is in DB
# - Verify reservations is empty
function test_01_list_empty_reservations
{
    test_output="$test_dir/01_list_reservations_empty_db.html"
    do_curl_as_admin 'gestion/list_reservations.cgi' "$test_output.tmp"
    csrf_token="$(sed -n -e 's/.*csrf_token" value="\([a-f0-9A-F]*\)".*/\1/p' "$test_output.tmp")"
    if [ -z "$csrf_token" ];
    then
        die "No csrf_token in '$test_output.tmp'"
    else
        sed -e 's/csrf_token" value="'"$csrf_token"'"/csrf_token" value="CSRF_TOKEN"/g' \
            "$test_output.tmp" \
            > "$test_output"
    fi
    do_diff "$test_output"
    get_db_file
    if [ "$(count_reservations)" != "0" ]; then
        die "Reservations table is not empty."
    fi
    if [ "$(count_csrfs)" != "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
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
    test_output="$test_dir/02_invalid_date_for_reservation.html"
    do_curl 'post_reservation.cgi' "$test_output" "-X POST -F name=TestName -F email=Test.Email@example.com -F date=1234-56-78 -F paying_seats=3 -F free_seats=5 -F gdpr_accepts_use=1"
    do_diff "$test_output"
    get_db_file
    if [ "$(count_reservations)" != "0" ]; then
        die "test_02_invalid_date_for_reservation: Reservations table is not empty."
    fi
    if [ "$(count_csrfs)" != "1" ]; then
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
                                                 TestName Test.Email@example.com \
                                                 2099-01-01 3 5 1500 1 1
}

# 04: Register for Saturday
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_04_valid_reservation_for_saturday
{
    generic_test_valid_reservation_for_test_date 04_valid_reservation_for_saturday \
                                                 Saturday Saturday@gmail.com \
                                                 2021-12-04 4 1 2000 1 2
}

# 05: Register for Sunday
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_05_valid_reservation_for_sunday
{
    generic_test_valid_reservation_for_test_date 05_valid_reservation_for_sunday \
                                                 Sunday SundayMail@gmx.com \
                                                 2021-12-05 1 1 500 0 3
}

# 06: List reservations with new content, limit & sorting options
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_06_list_reservations
{
    test_output="$test_dir/06_list_reservations.html"
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=7&offset=1&sort_order=date&sort_order=name' "$test_output.tmp"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    if [ "$(count_csrfs)" != "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    sunday_bank_id="$(sql_query "SELECT bank_id FROM reservations WHERE name = 'Sunday';")"
    testname_bank_id="$(sql_query "SELECT bank_id FROM reservations WHERE name = 'TestName';")"
    csrf_token="$(sed -n -e 's/.*csrf_token" value="\([a-f0-9A-F]*\)".*/\1/p' "$test_output.tmp")"
    if [ -z "$csrf_token" ];
    then
        die "No csrf_token in '$test_output.tmp'"
    else
        sed -e 's/csrf_token" value="'"$csrf_token"'"/csrf_token" value="CSRF_TOKEN"/g' \
            -e "s/$sunday_bank_id/COMMUNICATION Sunday/g" \
            -e "s/$testname_bank_id/COMMUNICATION TestName/g" \
            "$test_output.tmp" \
            > "$test_output"
    fi
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
    test_output="$test_dir/09_new_reservation_with_correct_CSRF_token_succeeds.html"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    do_curl_as_admin 'gestion/add_unchecked_reservation.cgi' \
                     "$test_output" \
                     "-X POST -F name=TestCreatedByAdmin -F comment=ByAdmin -F date=2099-01-01 -F paying_seats=0 -F free_seats=1 -F csrf_token=$csrf_token"
    communication="$(sed -n -e 's;.*<code>\(+++[0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9][0-9]+++\)</code>.*;\1;p' "$test_output")"
    if [ -n "$communication" ]; then
       die "test_09_new_reservation_with_correct_CSRF_token_succeeds: bank ID in output"
    fi
    get_db_file
    if [ "$(count_csrfs)" != "1" ]; then
        die ": CSRF problem: new CSRF token created."
    fi
    if [ "$(count_reservations)" != "4" ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: Reservations table should contain $total_reservations_count row."
    fi
    if [ "$(sql_query "SELECT name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, active FROM reservations ORDER BY time DESC LIMIT 1;")" \
             != "TestCreatedByAdmin|ByAdmin|2099-01-01|0|1|0|0|1" \
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
    test_output="$test_dir/10_export_as_csv.csv"
    do_curl_as_admin 'gestion/export_csv.cgi' "$test_output.tmp"
    # Replace variable or random parts of collected output by deterministic identifiers
    substitutions="$(sql_query "SELECT name, bank_id FROM reservations" \
                         | sed -e 's;\(.*\)|\(...\)\(....\)\(.....\);-e s,+++\2/\3/\4+++,COMMUNICATION-\1,;')"
    sed $substitutions -e "s/,$admin_user,/,TEST_ADMIN,/" "$test_output.tmp" > "$test_output"
    do_diff "$test_output"
    echo "test_10_export_as_csv: ok"
}

# Deploy
"$(dirname "$0")/../deploy.sh" "$destination" "$user" "$group" "$ssh_app_folder" "$admin_user" "$admin_pw"
echo '{ "paying_seat_cents": 500 }' \
    | ssh "$destination" \
          "touch '$ssh_app_folder/configuration.json'; cat > '$ssh_app_folder/configuration.json'"

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

# Clean up
ssh $destination "rm -r '$host_path_prefix/$folder'"
rm -r "$test_dir"

echo Done
