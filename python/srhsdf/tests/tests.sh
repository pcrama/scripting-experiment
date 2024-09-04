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
bank_account="BE5112$pseudo_random"
info_email="mrx.$pseudo_random@example.com"

if [ -z "$skip_deploy" -a '(' -z "$host_path_prefix" -o -z "$base_url" -o -z "$destination" -o -z "$user" -o -z "$group" ')' ];
then
    echo "Missing parameters: '$0'$dash_x$skip_deploy '$base_url' '$host_path_prefix' '$destination' '$user' '$group' '$venv_abs_path' '$admin_user' '$admin_pw'"
    echo "Usage: $(basename "$0") [-x] [-f] <host-for-base-url> <abs-host-path-prefix> <ssh-host> <user> <group> [<venv-abs-path> [<admin-user> [<admin-pw>]]]"
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

function assert_redirect_to_concert_page
{
    local test_stderr
    test_stderr="$1"
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr" \
        || die "Not a redirect: $test_stderr $2"
    grep -q '^< Location: https://www.srhbraine.be' "$test_stderr" \
        || die "Target is not srhbraine.be: $test_stderr $2"
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
    grep -q '^< HTTP/1.1 302 Found' "$test_stderr" "" || die "Not a redirect: $test_stderr"
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

function count_active_payments {
    sql_query "SELECT COUNT(*) FROM payments WHERE active=1;"
}

function get_user_of_csrf_token {
    sql_query "SELECT user FROM csrfs WHERE token='$1';"
}

function get_remote_addr_of_csrf_token {
    sql_query "SELECT ip FROM csrfs WHERE token='$1';"
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
    local test_name spectator_name spectator_email concert_date paying_seats free_seats cents_due gdpr_accepts_use total_reservations_count test_output communication formatted_communication
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
    do_curl_with_redirect 'post_reservation.cgi' \
                          "$test_output.tmp" \
                          "-X POST -F name=$spectator_name -F email=$spectator_email -F date=$concert_date -F paying_seats=$paying_seats -F free_seats=$free_seats -F gdpr_accepts_use=$gdpr_accepts_use"
    get_db_file
    communication="$(sed -n -e 's;.*<code>+++\([0-9][0-9][0-9]\)/\([0-9][0-9][0-9][0-9]\)/\([0-9][0-9][0-9][0-9][0-9]\)+++</code>.*;\1\2\3;p' "$test_output.tmp")"
    formatted_communication="$(sed -n -e 's;.*<code>\(+++[0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9][0-9]+++\)</code>.*;\1;p' "$test_output.tmp")"
    if [ -z "$communication" ]; then
       die "test_$test_name: no bank ID"
    fi
    sed -e "s;$formatted_communication;COMMUNICATION;g" \
        -e "s;$bank_account;BANK_ACCOUNT;g" \
        -e "s;$communication;COMMUNICATION;g" \
        -e "s;uuid_hex=[a-f0-9]*;uuid_hex=UUID_HEX;g" \
        -e "s;<svg .*</svg><br>La;svg<br>La;" \
        -e "s;<svg .*</svg></p>;svg</p>;" \
        "$test_output.tmp" \
        > "$test_output"
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
    if [ "$(sql_query "SELECT name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, active, bank_id FROM reservations WHERE bank_id = '$communication';")" \
             != "$spectator_name|$spectator_email|$concert_date|$paying_seats|$free_seats|$gdpr_accepts_use|$cents_due|1|$communication" \
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
                     "-X POST -F name=$test_name -F email=ByAdminNoCsrf@email.com -F date=2099-01-01 -F paying_seats=3 -F free_seats=5 $csrf_arg --verbose" \
                     2> "$test_stderr"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    assert_redirect_to_concert_page "$test_stderr" "gestion/add_unchecked_reservation.cgi without valid CSRF token should fail"
    echo "test_$test_name: ok"
}

# Assumes up to date DB is available (see get_db_file), validates that the
# CSRF token is included.  Output to stdout.
function make_list_reservations_output_deterministic
{
    local input substitutions csrf_token
    input="$1"
    # tr -d -c '...': slugify name to ensure it can become a proper sed(1) command
    substitutions="$(sql_query "SELECT name, bank_id FROM reservations" \
                         | tr -d -c 'a-zA-Z0-9|\n' \
                         | sed -e 's;\(.*\)|\(.*\);-e s,\2,COMMUNICATION-\1,;')"
    csrf_token="$(sed -n -e 's/.*csrf_token" value="\([a-f0-9A-F]*\)".*/\1/p' "$input")"
    if [ -z "$csrf_token" ];
    then
        die "No csrf_token in '$input'"
    else
        sed -e 's/csrf_token" value="'"$csrf_token"'"/csrf_token" value="CSRF_TOKEN"/g' \
            $substitutions \
            -e "s/$admin_user/TEST_ADMIN/g" \
            -e "s;<td>[0-9]*/[0-9]*/[0-9]* [0-9]*:[0-9]*</td></tr>;<td>TEST-DATE</td></tr>;g" \
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
                   CONFIGURATION_JSON_DIR="$test_dir" \
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
    local ignore_cgitb remote_addr test_name method script_name query_string test_output
    if [ "$1" = "--ignore-cgitb" ]; then
        ignore_cgitb="$1"
        shift
    else
        ignore_cgitb=""
    fi
    if [ "$1" = "--remote-addr" ]; then
        remote_addr="$2"
        shift 2
    else
        remote_addr="1.2.3.4"
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
    if ! simulate_cgi_request "$method" "$admin_sub_dir/$script_name" "$query_string" REMOTE_USER="$admin_user" REMOTE_ADDR="$remote_addr" "$@" > "$test_output" ; then
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
        grep -q '</title><link rel="stylesheet"[^>]*bootstrap[^>]*>.*<body>.*<nav id="navbar"' "$test_output" || die "$test_name no banner in $test_output"
    else
        if grep -q '<img src="https://www.srhbraine.be/images/logo-srh.png"' "$test_output"; then
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

# Test definitions

# 01: Post a new reservation as a customer
function test_01_local_post_reservation
{
    local test_name test_output uuid_hex bank_id
    test_name="test_01_local_post_reservation"
    test_output="$test_dir/$test_name.log"
    echo | (cd "$app_dir" && script_name=post_reservation.cgi && env CONFIGURATION_JSON_DIR="$test_dir" REQUEST_METHOD=POST 'QUERY_STRING=civility=melle&first_name=Jean&last_name=test&email=i%40example.com&paying_seats=3&free_seats=2&gdpr_accepts_use=true&date=2099-01-01' SERVER_NAME=example.com SCRIPT_NAME=$script_name python3 $script_name) > "$test_output" 2> "$test_output.stderr"
    grep -q '^Status: 302' "$test_output"
    uuid_hex="$(sed -n -e '/^Location: /s/.*uuid_hex=\([a-f0-9]*\).*/\1/p' "$test_output")"
    [ -z "$uuid_hex" ] && die "No uuid_hex in $test_output"
    bank_id="$(sed -n -e '/^Location: /s/.*bank_id=\([0-9]*\).*/\1/p' "$test_output")"
    [ -z "$bank_id" ] && die "No bank_id in $test_output"
    [ "$(count_reservations)" -eq 1 ] || die "Reservation count wrong"
    [ "$(count_csrfs)" -eq 0 ] || die "CSRF count wrong"
    [ "$(count_payments)" -eq 0 ] || die "Payment count wrong"
    (cd "$app_dir" && script_name=show_reservation.cgi && env CONFIGURATION_JSON_DIR="$test_dir" REQUEST_METHOD=GET QUERY_STRING="bank_id=$bank_id&uuid_hex=$uuid_hex" SERVER_NAME=example.com SCRIPT_NAME=$script_name python3 $script_name) > "$test_output" 2> "$test_output.stderr"
    assert_html_response "$test_name" "$test_output" \
                         "Melle Jean test" \
                         " 3 [^0-9]*pay[^0-9]* 2 [^0-9]*gratuit" \
                         "$bank_account" \
                         "$(echo $bank_id | sed -e 's;\(...\)\(....\)\(.*\);\1/\2/\3;')" \
                         "$bank_id" \
                         "$uuid_hex"
    [ "$(count_reservations)" -eq 1 ] || die "Reservation count wrong"
    [ "$(count_csrfs)" -eq 0 ] || die "CSRF count wrong"
    [ "$(count_payments)" -eq 0 ] || die "Payment count wrong"
    echo "$test_name: ok"
}

# 02: Locally list payments when DB is still empty
function test_02_local_list_empty_payments
{
    local test_output csrf_token
    test_output="$test_dir/02_local_list_empty_payments.html"
    (cd "$app_dir/gestion" && env CONFIGURATION_JSON_DIR="$test_dir" REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=list_payments.cgi python3 list_payments.cgi) > "$test_output.tmp"
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
    if [ "$(count_csrfs)" -ne "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "secretaire" ]; then
        die "CSRF problem."
    fi
    echo "test_02_local_list_empty_payments: ok"
}

function test_03_local_list_reservations__1_reservation
{
    local test_name test_output csrf_token local_user
    test_name="03_local_list_reservations__1_reservation"
    test_output="$test_dir/$test_name.html"
    local_user=secretaire
    (cd "$app_dir/gestion";export SCRIPT_NAME="list_reservations.cgi"; cd "$(dirname "$SCRIPT_NAME")" && CONFIGURATION_JSON_DIR="$(dirname "$(ls -t /tmp/tmp.*/configuration.json | head -n 1)")" DB_DB="$CONFIGURATION_JSON_DIR/db.db" REQUEST_METHOD=GET REMOTE_USER="$local_user" REMOTE_ADDR="1.2.3.4" QUERY_STRING="" SERVER_NAME=localhost python3 $SCRIPT_NAME) > "$test_output"
    [ "$(count_reservations)" -eq 1 ] || die "Reservation count wrong"
    [ "$(count_csrfs)" -eq 1 ] || die "CSRF count wrong"
    [ "$(count_payments)" -eq 0 ] || die "Payment count wrong"
    csrf_token="$(get_csrf_token_of_user "$local_user")"
    [ -n "$csrf_token" ] || die "Unable to get csrf_token of $local_user"
    assert_html_response "$test_name" "$test_output" \
                         "<tr><td>Melle Jean test</td><td>i@example.com</td><td>2099-01-01</td><td>3</td><td>2</td>" \
                         '<input type="hidden"[^>]*"csrf_token"[^>]*"'"$csrf_token"'"'
    echo "$test_name: ok"
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
    do_curl 'post_reservation.cgi' "$test_output" "-X POST -F name=TestName -F email=Test.Email@example.com -F date=1234-56-78 -F paying_seats=3 -F free_seats=5 -F gdpr_accepts_use=1"
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
                                                 TestName Test.Email@example.com \
                                                 2099-01-01 3 5 1500 1 1
}

function test_03_00_locally_upload_payments
{
    local test_name test_output uuid_hex content_boundary row_count bank_transaction_number csrf_token remote_addr year_prefix
    test_name="test_03_00_locally_upload_payments"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    remote_addr="$(get_remote_addr_of_csrf_token "$csrf_token")"
    if [ -z "$remote_addr" ]; then
       die "$test_name no REMOTE_ADDR generated for $admin_user"
    fi
    uuid_hex="$(sql_query 'select uuid from reservations where name="TestName" limit 1')"
    if [ -z "$uuid_hex" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    bank_transaction_number="$(get_bank_id_from_reservation_uuid "$uuid_hex")"
    if [ -z "$bank_transaction_number" ]; then
        die "$test_name Unable to find bank transaction number"
    fi
    year_prefix="$(date +%Y)"
    content_boundary='95173680fbda20e37a8df066f0d77cc4'
    export CONTENT_STDIN="--${content_boundary}
Content-Disposition: form-data; name=\"csrf_token\"

$csrf_token
--${content_boundary}
Content-Disposition: form-data; name=\"csv_file\"; filename=\"test.csv\"
Content-Type: text/csv

Nº de séquence;Date d'exécution;Date valeur;Montant;Devise du compte;Numéro de compte;Type de transaction;Contrepartie;Nom de la contrepartie;Communication;Détails;Statut;Motif du refus
${year_prefix}-00127;28/03/2023;28/03/2023;18;EUR;BE00010001000101;Virement en euros;BE00020002000202;ccccc-ccccccccc;reprise marchandise;VIREMENT EN EUROS DU COMPTE BE00020002000202 BIC GABBBEBB CCCCC-CCCCCCCCC AV DE LA GARE 76 9999 WAGADOUGOU COMMUNICATION : REPRISE MARCHANDISE REFERENCE BANQUE : 2303244501612 DATE VALEUR : 28/03/2023;Accepté;
${year_prefix}-00119;25/03/2023;24/03/2023;27;EUR;BE00010001000101;Virement instantané en euros;BE100010001010;SSSSSS GGGGGGGG;${bank_transaction_number};VIREMENT INSTANTANE EN EUROS BE10 0010 0010 10 BIC GABBBEBBXXX SSSSSS GGGGGGGG RUE MARIGNON 43/5 8888 BANDARLOG COMMUNICATION : xxx EXECUTE LE 24/03 REFERENCE BANQUE : 2303244502842 DATE VALEUR : 24/03/2023;Accepté;


--${content_boundary}
Content-Disposition: form-data; name=\"submit\"

Importer les extraits de compte
--${content_boundary}--
"
    test_output="$(capture_admin_cgi_output --remote-addr "${remote_addr}" "${test_name}" POST import_payments.cgi "" CONTENT_TYPE="multipart/form-data; boundary=$content_boundary")"
    export CONTENT_STDIN=""
    grep -q "^Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    target="gestion/list_payments.cgi"
    grep -q "^Location: .*$target" "$test_output" || die "$test_name not redirecting to correct target \`\`$target'' in $test_output"
    if ! row_count="$(count_payments)" ; then
        die "$test_name Could not count payments"
    else
        [ "$row_count" -eq 2 ] || die "$test_name Unexpected row_count=$row_count"
    fi
}

function test_03_01_locally_hide_payment
{
    local test_name test_output uuid_hex content_boundary row_count bank_ref csrf_token remote_addr year_prefix
    test_name="test_03_01_locally_hide_payment"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    if [ -z "$csrf_token" ]; then
       die "$test_name no CSRF token generated for $admin_user"
    fi
    remote_addr="$(get_remote_addr_of_csrf_token "$csrf_token")"
    if [ -z "$remote_addr" ]; then
       die "$test_name no REMOTE_ADDR generated for $admin_user"
    fi
    uuid_hex="$(sql_query 'select uuid from reservations where name="TestName" limit 1')"
    if [ -z "$uuid_hex" ]; then
        die "$test_name Unable to find reservation uuid"
    fi
    bank_ref="2303244502842"
    year_prefix="$(date +%Y)"
    content_boundary='95173680fbda20e37a8df066f0d77cc4'
    export CONTENT_STDIN="--${content_boundary}
Content-Disposition: form-data; name=\"csrf_token\"

$csrf_token
--${content_boundary}
Content-Disposition: form-data; name=\"bank_ref\"

${bank_ref}
--${content_boundary}
Content-Disposition: form-data; name=\"submit\"

Importer les extraits de compte
--${content_boundary}--
"
    test_output="$(capture_admin_cgi_output --remote-addr "${remote_addr}" "${test_name}" POST hide_payment.cgi "" CONTENT_TYPE="multipart/form-data; boundary=$content_boundary")"
    export CONTENT_STDIN=""
    grep -q "^Status: 302" "$test_output" || die "$test_name No Status: 302 redirect in $test_output"
    target="gestion/list_payments.cgi"
    grep -q "^Location: .*$target" "$test_output" || die "$test_name not redirecting to correct target \`\`$target'' in $test_output"
    if ! row_count="$(count_payments)" ; then
        die "$test_name Could not count payments"
    else
        [ "$row_count" -eq 2 ] || die "$test_name Unexpected row_count=$row_count"
    fi
    if ! row_count="$(count_active_payments)" ; then
        die "$test_name Could not count active payments"
    else
        [ "$row_count" -eq 1 ] || die "$test_name Unexpected row_count=$row_count"
    fi
}

# 04: Register for Saturday
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_04_valid_reservation_for_saturday
{
    generic_test_valid_reservation_for_test_date 04_valid_reservation_for_saturday \
                                                 Saturday Saturday@gmail.com \
                                                 2024-11-30 4 1 2000 1 2
}

# 05: Register for Sunday
# - Verify output HTML
# - Verify reservations contains 1 row with correct information
# - No new CSRF token
function test_05_valid_reservation_for_sunday
{
    generic_test_valid_reservation_for_test_date 05_valid_reservation_for_sunday \
                                                 Sunday SundayMail@gmx.com \
                                                 2024-12-01 1 1 500 0 3
}

# 06: List reservations with new content, limit & sorting options
# - Verify output HTML
# - Verify CSRF is in DB (no new CSRF token created)
function test_06_list_reservations
{
    local test_output csrf_token
    test_output="$test_dir/06_list_reservations.html"
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=7&offset=1&sort_order=date&sort_order=name' "$test_output.tmp"
    csrf_token="$(sed -n -e 's/.*csrf_token" value="\([a-f0-9A-F]*\)".*/\1/p' "$test_output.tmp")"
    get_db_file
    if [ "$(count_reservations)" != "3" ]; then
        die "Reservations table wrong."
    fi
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    make_list_reservations_output_deterministic "$test_output.tmp" > "$test_output"
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
    local test_output csrf_token bank_id formatted_communication uuid_hex
    test_output="$test_dir/09_new_reservation_with_correct_CSRF_token_succeeds.html"
    csrf_token="$(get_csrf_token_of_user "$admin_user")"
    do_curl_with_redirect --admin \
                          'gestion/add_unchecked_reservation.cgi' \
                          "$test_output.tmp" \
                          "-X POST -F name=TestCreatedByAdmin -F comment=ByAdmin -F date=2099-01-01 -F paying_seats=0 -F free_seats=1 -F csrf_token=$csrf_token"
    formatted_communication="$(sed -n -e 's;.*<code>\(+++[0-9][0-9][0-9]/[0-9][0-9][0-9][0-9]/[0-9][0-9][0-9][0-9][0-9]+++\)</code>.*;\1;p' "$test_output.tmp")"
    if [ -n "$formatted_communication" ]; then
       die "test_09_new_reservation_with_correct_CSRF_token_succeeds: bank ID '$formatted_communication' in output"
    fi
    bank_id="$(sed -n -e 's;.*show_reservation.cgi[^"]*bank_id=\([0-9]*\).*;\1;p' "$test_output.tmp")"
    if [ -z "$bank_id" ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: bank ID not in link or link not found"
    fi
    uuid_hex="$(sed -n -e 's;.*show_reservation.cgi[^"]*uuid_hex=\([a-f0-9]*\).*;\1;p' "$test_output.tmp")"
    if [ -z "$uuid_hex" ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: uuid hex not in link or link not found"
    fi
    get_db_file
    if [ "$(count_csrfs)" -gt "1" ]; then
        die ": CSRF problem: new CSRF token created."
    fi
    if [ "$(count_reservations)" != "4" ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: Reservations table should contain $total_reservations_count row."
    fi
    if [ "$(sql_query "SELECT name, email, date, paying_seats, free_seats, gdpr_accepts_use, cents_due, active, bank_id, uuid FROM reservations ORDER BY timestamp DESC LIMIT 1;")" \
             != "TestCreatedByAdmin|ByAdmin|2099-01-01|0|1|0|0|1|$bank_id|$uuid_hex" \
       ]; then
        die "test_09_new_reservation_with_correct_CSRF_token_succeeds: Wrong data saved in DB"
    fi
    sed -e "s;$bank_account;BANK_ACCOUNT;g" \
        -e "s;$bank_id;COMMUNICATION;g" \
        -e "s;uuid_hex=[a-f0-9]*;uuid_hex=UUID_HEX;g" \
        -e "s;<svg .*</svg><br>La;svg<br>La;" \
        -e "s;<svg .*</svg></p>;svg</p>;" \
        "$test_output.tmp" \
        > "$test_output"
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
    # Replace variable or random parts of collected output by deterministic identifiers
    substitutions="$(sql_query "SELECT name, bank_id FROM reservations" \
                         | sed -e 's;\(.*\)|\(...\)\(....\)\(.....\);-e s,+++\2/\3/\4+++,COMMUNICATION-\1,;')"
    sed $substitutions -e "s/,$admin_user,/,TEST_ADMIN,/" "$test_output.tmp" > "$test_output"
    do_diff "$test_output"
    echo "test_10_export_as_csv: ok"
}

# 11: Deactivate first reservation to check it does not show up in the list anymore
function test_11_deactivate_a_reservation
{
    local test_output
    sql_query 'UPDATE reservations SET active=0 WHERE bank_id = (
                   SELECT bank_id FROM reservations ORDER BY timestamp ASC LIMIT 1)'
    put_db_file
    test_output="$test_dir/11_deactivate_a_reservation.html"
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=17&sort_order=PAYING_SEATS&sort_order=name' "$test_output.tmp"
    make_list_reservations_output_deterministic "$test_output.tmp" > "$test_output"
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
                                                 2024-11-30 7 2 3500 0 5
    do_curl_as_admin 'gestion/list_reservations.cgi?limit=9' "$test_output.tmp"
    csrf_token="$(sed -n -e 's/.*csrf_token" value="\([a-f0-9A-F]*\)".*/\1/p' "$test_output.tmp")"
    get_db_file
    sql_query 'select email,name from reservations where email like "%body%html%"' \
              > "$sql_output"
    do_diff "$sql_output"
    if [ "$(count_csrfs)" -gt "1" -o "$(get_user_of_csrf_token "$csrf_token")" != "$admin_user" ]; then
        die "CSRF problem."
    fi
    make_list_reservations_output_deterministic "$test_output.tmp" > "$test_output"
    do_diff "$test_output"
    echo "test_12_bobby_tables_and_co: ok"
}

# 13: Try to display a reservation with insufficient or wrong input data to identify it
# Must redirect to concert page
function test_13_show_reservation_redirects_to_concert_page_on_error
{
    local valid_uuid other_valid_uuid valid_bank_id test_output test_stderr
    valid_uuid="$(sql_query 'select uuid from reservations limit 1')"
    other_valid_uuid="$(sql_query "select uuid from reservations where uuid != '$valid_uuid' limit 1")"
    valid_bank_id="$(sql_query "select bank_id from reservations where uuid = '$valid_uuid' limit 1")"
    test_output="$test_dir/13_show_reservation_redirects_to_concert_page_on_error.html"
    test_stderr="$test_dir/13_show_reservation_redirects_to_concert_page_on_error.stderr.log"
    do_curl 'show_reservation.cgi' "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page "$test_stderr" "show_reservation.cgi without query parameters"
    do_curl "show_reservation.cgi?bank_id=$valid_bank_id" "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page "$test_stderr" "show_reservation.cgi with valid bank_id, no uuid"
    do_curl "show_reservation.cgi?uuid_hex=$valid_uuid" "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page "$test_stderr" "show_reservation.cgi with valid uuid, no bank_id"
    do_curl "show_reservation.cgi?uuid_hex=$other_valid_uuid&bank_id=$valid_bank_id" "$test_output" --verbose 2> "$test_stderr"
    assert_redirect_to_concert_page "$test_stderr" "show_reservation.cgi with valid uuid, unrelated existing bank_id"
    do_curl "show_reservation.cgi?uuid_hex=$valid_uuid&bank_id=$valid_bank_id" "$test_output" --verbose 2> "$test_stderr"
    grep -q '< HTTP/1.1 200' "$test_stderr" \
         || die "Failed to get show_reservation.cgi?uuid_hex=$valid_uuid&bank_id=$valid_bank_id"
    echo "test_13_show_reservation_redirects_to_concert_page_on_error: ok"
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

# Local copy of configuration
echo '{ "paying_seat_cents": 500, "bank_account": "'$bank_account'", "info_email": "'$info_email'", "dbdir": "'$test_dir'", "logir": "'$test_dir'" }' \
     > "$test_dir/configuration.json"

if [ -n "$dash_x" ];
then
    set -x
fi

test_01_local_post_reservation
test_02_local_list_empty_payments
test_03_local_list_reservations__1_reservation

set +x

if [ -n "$skip_deploy" ];
then
    echo "Everything is fine so far.  Skipping tests requiring deployment -> cleaning $test_dir"
    rm -rf "$test_dir"
    exit 0
fi

ssh_app_folder="$host_path_prefix/$folder"
cat <<EOF
Deploying to '$ssh_app_folder', clean with
    ssh '$destination' "rm -r '$ssh_app_folder' '$venv_abs_path'";
EOF

# Deploy
"$(dirname "$0")/../deploy.sh" "--for-tests" "$destination" "$user" "$group" "$host_path_prefix" "$folder" "$venv_abs_path" "$admin_user" "$admin_pw"
cat "$test_dir/configuration.json" \
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
test_03_00_locally_upload_payments
test_03_01_locally_hide_payment
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

set +x

# Clean up
ssh $destination "rm -r '$host_path_prefix/$folder' ; if [ -r '$venv_abs_path/.ssh' ] ; then echo '\"$venv_abs_path\" might be your home directory, not cleaning up' ; else if [ -r '$venv_abs_path/bin/activate' -a -r '$venv_abs_path/pyvenv.cfg' ] ; then rm -r '$venv_abs_path' ; else echo 'I am not comfortable rm -r \"$venv_abs_path\"' ; fi ; fi"
rm -r "$test_dir"

echo Done

# Local Variables:
# compile-command: "time ./tests.sh -x -f"
# End:
