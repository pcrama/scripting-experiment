#!/usr/pkg/bin/python3
# -*- coding: utf-8 -*-
#
# Test with
#
# (cd app/gestion && env REQUEST_METHOD=GET REMOTE_USER=secretaire REMOTE_ADDR=1.2.3.4 SERVER_NAME=localhost SCRIPT_NAME=list_reservations.cgi python list_reservations.cgi)

import cgi
import cgitb
import itertools
import os
import sys
import time
from typing import Optional
import urllib.parse

# hack to get at my utilities:
sys.path.append('..')
import config
from htmlgen import (
    format_bank_id,
    html_document,
    pluriel_naif,
    print_content_type,
    redirect_to_event,
    respond_html,
)
from lib_post_reservation import (
    make_show_reservation_url
)
import pricing
from storage import (
    Csrf,
    Reservation,
    create_db,
)
from create_tickets import (
    ul_for_menu_data,
)

def multi_replace(s: str, replaces: list[tuple[str, str]]) -> str:
    for pattern, new_value in replaces:
        s = s.replace(pattern, new_value)
    return s


def update_sort_order(new_col_name, sort_order):
    if sort_order:
        if new_col_name.upper() == sort_order[0]:
            return sort_order[1:]
        elif new_col_name.lower() == sort_order[0]:
            return [new_col_name.upper(), *(x for x in sort_order if x.lower() != new_col_name.lower())]
        else:
            return [new_col_name.lower(), *(x for x in sort_order if x.lower() != new_col_name.lower())]
    else:
        return [new_col_name]


def make_url(sort_order, limit, offset, base_url=None, environ=None):
    if base_url is None:
        environ = environ or os.environ
        base_url = urllib.parse.urljoin(f'https://{environ["SERVER_NAME"]}', environ["SCRIPT_NAME"])
    params = list((k, v) for k, v in itertools.chain(
        (('limit', limit),
         ('offset', offset)),
        (('sort_order', s) for s in sort_order))
                  if v is not None)
    split_result = urllib.parse.urlsplit(base_url)
    return urllib.parse.urlunsplit((
        split_result.scheme,
        split_result.netloc,
        split_result.path,
        urllib.parse.urlencode(params),
        split_result.fragment))


def make_navigation_a_elt(sort_order, limit, offset, text):
    return (('a',
             'class', 'navigation',
             'href', make_url(sort_order, limit, offset)),
            text)


def get_first(d, k):
    return d.get(k, [None])[0]


def sort_direction(col, sort_order):
    col = col.lower()
    if sort_order and sort_order[0].lower() == col:
        return ' ⬇' if sort_order[0].isupper() else ' ⬆'
    try:
        sort_col = next(x for x in sort_order if x.lower() == col)
        return ' ↓' if sort_col[0].isupper() else ' ↑'
    except StopIteration:
        return ''


def make_show_reservation_link_elt(r, link_text):
    return (
        ('a',
         'href',
         make_show_reservation_url(
             r.uuid,
             script_name=os.path.dirname(os.environ["SCRIPT_NAME"]))),
        link_text)


def make_sum_group(div_id: str, div_class: str, error_msg: Optional[str], inputs_and_labels: list[tuple[str, str]]):
    return (('div', 'class', div_class, 'id', div_id),
            *([] if error_msg is None else [(('div', 'class', 'error-message'), error_msg)]),
            *(make_label_and_input(*data) for data in inputs_and_labels))


def make_label_and_input(input_id: str, label: str):
    return ('div',
            (('label', 'for', input_id), label),
            (('input', 'min', '0', 'max', '50', 'size', '5', 'type', 'number', 'id', input_id, 'name', input_id, 'value', '0'),))


DEFAULT_LIMIT = 20
MAX_LIMIT = 500

if __name__ == '__main__':
    if os.getenv('REQUEST_METHOD') != 'GET' or any(
            os.getenv(p) is None for p in (
                'REMOTE_USER', 'REMOTE_ADDR', 'SERVER_NAME', 'SCRIPT_NAME')):
        redirect_to_event()

    CONFIGURATION = config.get_configuration()
    cgitb.enable(display=CONFIGURATION['cgitb_display'], logdir=CONFIGURATION['logdir'])

    MAIN_STARTER = CONFIGURATION["main_starter_name"]
    MAIN_STARTER_SHORT = CONFIGURATION["main_starter_short"]
    EXTRA_STARTER = CONFIGURATION["extra_starter_name"]
    EXTRA_STARTER_SHORT = CONFIGURATION["extra_starter_short"]
    MAIN_DISH = CONFIGURATION["main_dish_name"]
    MAIN_DISH_SHORT = CONFIGURATION["main_dish_short"]
    EXTRA_DISH = CONFIGURATION["extra_dish_name"]
    EXTRA_DISH_SHORT = CONFIGURATION["extra_dish_short"]
    THIRD_DISH = CONFIGURATION["third_dish_name"]
    THIRD_DISH_SHORT = CONFIGURATION["third_dish_short"]
    KIDS_MAIN_DISH = CONFIGURATION["kids_main_dish_name"]
    KIDS_MAIN_DISH_SHORT = CONFIGURATION["kids_main_dish_short"]
    KIDS_EXTRA_DISH = CONFIGURATION["kids_extra_dish_name"]
    KIDS_EXTRA_DISH_SHORT = CONFIGURATION["kids_extra_dish_short"]
    KIDS_THIRD_DISH = CONFIGURATION["kids_third_dish_name"]
    KIDS_THIRD_DISH_SHORT = CONFIGURATION["kids_third_dish_short"]
    MAIN_DESSERT = CONFIGURATION["main_dessert_name"]
    MAIN_DESSERT_SHORT = CONFIGURATION["main_dessert_short"]
    EXTRA_DESSERT = CONFIGURATION["extra_dessert_name"]
    EXTRA_DESSERT_SHORT = CONFIGURATION["extra_dessert_short"]
    INFO_EMAIL = CONFIGURATION["info_email"]

    try:
        params = cgi.parse()
        sort_order = params.get('sort_order', '')
        try:
            limit = min(int(get_first(params, 'limit') or DEFAULT_LIMIT), MAX_LIMIT)
        except Exception:
            limit = DEFAULT_LIMIT
        try:
            offset = max(int(get_first(params, 'offset')), 0)
        except Exception:
            offset = 0
        connection = create_db(CONFIGURATION)
        csrf_token = Csrf.get_by_user_and_ip(
            connection, os.getenv('REMOTE_USER'), os.getenv('REMOTE_ADDR'))

        COLUMNS = [('name', 'Nom'), ('email', 'Email'), ('extra_comment', 'Commentaire'),
                   ('places', 'Places'),
                   ('main_starter', MAIN_STARTER_SHORT), ('extra_starter', EXTRA_STARTER_SHORT),
                   ('main_dish', MAIN_DISH_SHORT), ('extra_dish', EXTRA_DISH_SHORT), ('third_dish', THIRD_DISH_SHORT),
                   ('kids_main_dish', KIDS_MAIN_DISH_SHORT), ('kids_extra_dish', KIDS_EXTRA_DISH_SHORT), ('kids_third_dish', KIDS_THIRD_DISH_SHORT),
                   ('main_dessert', MAIN_DESSERT_SHORT), ('extra_dessert', EXTRA_DESSERT_SHORT),
                   ('bank_id', 'Transaction'), ('date', 'Date'),
                   ('time', 'Réservé le')]
        table_header_row = tuple(
            ('th', make_navigation_a_elt(update_sort_order(column, sort_order), limit, offset,
                                         header + sort_direction(column, sort_order)))
            for column, header in COLUMNS)
        total_bookings = Reservation.length(connection)
        (active_reservations,
         total_main_starter,
         total_extra_starter,
         total_main_dish,
         total_extra_dish,
         total_third_dish,
         total_kids_main_dish,
         total_kids_extra_dish,
         total_kids_third_dish,
         total_main_dessert,
         total_extra_dessert) = Reservation.count_menu_data(connection)
        reservation_summary = Reservation.summary_by_date(connection)
        pagination_links = tuple((
            x for x in
            [('li', make_navigation_a_elt(sort_order, limit, 0, 'Début'))
             if offset > 0
             else None,
             ('li',
              make_navigation_a_elt(sort_order, limit, offset - limit, 'Précédent'))
             if offset > limit else
             None,
             ('li',
              make_navigation_a_elt(sort_order, limit, offset + limit, 'Suivant'))
             if offset + limit < active_reservations else
             None]
            if x is not None))
        respond_html(html_document(
            'List of reservations',
            (*((('p',
                 'Il y a ', pluriel_naif(total_bookings, 'bulle'), ' en tout dont ',
                 pluriel_naif(active_reservations, ['est active', 'sont actives']),
                 '.'),
                ul_for_menu_data(total_main_starter, total_extra_starter,
                                 total_main_dish, total_extra_dish, total_third_dish,
                                 total_kids_main_dish, total_kids_extra_dish, total_kids_third_dish,
                                 total_main_dessert, total_extra_dessert)
                if sum((total_main_starter, total_extra_starter,
                        total_main_dish, total_extra_dish, total_third_dish,
                        total_kids_main_dish, total_kids_extra_dish, total_kids_third_dish,
                        total_main_dessert, total_extra_dessert)
                       ) > 0
                else '')
               if total_bookings > 0
               else []),
             ('ul', *tuple(('li', row[0], ': ',
                            pluriel_naif(row[1], ['place réservée', 'places réservées']))
                           for row in reservation_summary))
             if total_bookings > 0
             else '',
             (('form', 'action', os.getenv('SCRIPT_NAME')),
              (('label', 'for', 'limit'), 'Limiter le tableau à ', ('em', 'n'), ' lignes:'),
              (('input', 'id', 'limit', 'type', 'number', 'name', 'limit', 'min', '5', 'value', str(limit), 'max', '10000'),),
              (('input', 'type', 'submit', 'value', 'Rafraichir la page'),),
              *((('input', 'id', 'sort_order', 'name', 'sort_order', 'type', 'hidden', 'value', v),)
                for v in sort_order),
              (('input', 'id', 'offset', 'name', 'offset', 'type', 'hidden', 'value', str(offset)),)),
             (('ul', 'class', 'navbar'), *pagination_links) if pagination_links else '',
             (('table', 'class', 'list'),
              ('tr', *table_header_row),
              *tuple(('tr',
                      ('td', make_show_reservation_link_elt(r, r.name)),
                      ('td', make_show_reservation_link_elt(r, r.email)),
                      ('td', make_show_reservation_link_elt(r, r.extra_comment)),
                      ('td', r.places),
                      ('td', r.outside.main_starter + r.inside.main_starter),
                      ('td', r.outside.extra_starter + r.inside.extra_starter),
                      ('td', r.outside.main_dish + r.inside.main_dish),
                      ('td', r.outside.extra_dish + r.inside.extra_dish),
                      ('td', r.outside.third_dish + r.inside.third_dish),
                      ('td', r.kids.main_dish),
                      ('td', r.kids.extra_dish),
                      ('td', r.kids.third_dish),
                      ('td', r.outside.main_dessert + r.inside.main_dessert + r.kids.main_dessert),
                      ('td', r.outside.extra_dessert + r.inside.extra_dessert + r.kids.extra_dessert),
                      ('td', format_bank_id(r.bank_id)),
                      ('td', r.date),
                      ('td', time.strftime('%d/%m/%Y %H:%M', time.gmtime(r.timestamp))))
                     for r in Reservation.select(connection,
                                                 filtering=[('active', '1')],
                                                 order_columns=sort_order,
                                                 limit=limit,
                                                 offset=offset))),
             ('hr',),
             ('p',
              # name is a fake parameter to encourage clients to believe Excel
              # can really open it.
              (('a', 'href', 'export_csv.cgi?name=export.csv'),
               'Exporter en format CSV (Excel ou autres tableurs)'),
              '. Excel a du mal avec les accents et autres caractères spéciaux, voyez ',
              (('a', 'href', 'https://www.nextofwindows.com/how-to-display-csv-files-with-unicode-utf-8-encoding-in-excel'),
               'cette page'),
              " pour plus d'explications."),
             ('hr',),
             ('p', 'Ajouter une réservation:'),
             ('raw',
              multi_replace("""<script>
      document.addEventListener('DOMContentLoaded', function () {
          const errorClass = 'has-error';
          let form = document.querySelector('#reservation');

          let validations = [
              {'reference_fields': ['insidemaindish', 'insideextradish', 'insidethirddish'],
               'validations': [{'section': 'inside-menu-starter', 'validated_fields': ['insidemainstarter', 'insideextrastarter']},
                               {'section': 'inside-menu-dessert', 'validated_fields': ['insidemaindessert', 'insideextradessert']}]},
              {'reference_fields': ['kidsmaindish', 'kidsextradish', 'kidsthirddish'],
               'validations': [{'section': 'kids-menu-dessert', 'validated_fields': ['kidsmaindessert', 'kidsextradessert']}]}
          ];

          function sumOfInputFields(inputFieldIds) {
              return inputFieldIds.reduce((sum, fieldId) => sum + parseInt(document.getElementById(fieldId).value),
                                          0);
          }

          function runValidation(validation_suite) {
              let referenceSum = sumOfInputFields(validation_suite.reference_fields);
              validation_suite.validations.forEach(function(validation) {
                  var section = document.getElementById(validation.section);
                  var inputSum = sumOfInputFields(validation.validated_fields);

                  if (inputSum == referenceSum) {
                      section.classList.remove(errorClass);
                  } else {
                      section.classList.add(errorClass);
                  }
              });
          }

          function validateAll() {
              validations.forEach(runValidation);
          }

          form.addEventListener('submit', function (event) {
              // Reset error classes
              resetErrorClasses();

              validateAll();

              // Prevent form submission if there are errors
              if (form.querySelectorAll('.' + errorClass).length > 0) {
                  event.preventDefault();
              }
          });

          function updatePrice() {
              const prices = {
                  'insidemaindish': insidemaindish,,
                  'insideextradish': insideextradish,,
                  'insidethirddish': insidethirddish,,
                  'kidsmaindish': kidsmaindish,,
                  'kidsextradish': kidsextradish,,
                  'kidsthirddish': kidsthirddish,,
                  'outsidemainstarter': outsidemainstarter,,
                  'outsideextrastarter': outsideextrastarter,,
                  'outsidemaindish': outsidemaindish,,
                  'outsideextradish': outsideextradish,,
                  'outsidethirddish': outsidethirddish,,
                  'outsidemaindessert': outsidemaindessert,,
                  'outsideextradessert': outsideextradessert,
              };
              let totalPrice = 0;
              for (let key in prices) {
                  totalPrice += parseInt(document.getElementById(key).value) * prices[key];
              }
              let cents = String(totalPrice % 100).padStart(2, '0');
              document.getElementById('reservation-submit').value = totalPrice == 0?'Confirmer':`Prix total: ${totalPrice / 100}.${cents}€. Confirmer`
          }

          form.addEventListener('change', function (event) {
              validateAll();
              updatePrice();
          });

          function resetErrorClasses() {
              var errorSections = form.querySelectorAll('.' + errorClass);
              errorSections.forEach(function (section) {
                  section.classList.remove(errorClass);
              });
          }

          resetErrorClasses();
          validateAll();
          updatePrice();
      });
    </script>""", [
        (': insidemaindish,', f': {pricing.CENTS_MENU_MAIN_DISH}'),
        (': insideextradish,', f': {pricing.CENTS_MENU_EXTRA_DISH}'),
        (': insidethirddish,', f': {pricing.CENTS_MENU_THIRD_DISH}'),
        (': kidsmaindish,', f': {pricing.CENTS_KIDS_MENU_MAIN_DISH}'),
        (': kidsextradish,', f': {pricing.CENTS_KIDS_MENU_EXTRA_DISH}'),
        (': kidsthirddish,', f': {pricing.CENTS_KIDS_MENU_THIRD_DISH}'),
        (': outsidemainstarter,', f': {pricing.CENTS_STARTER}'),
        (': outsideextrastarter,', f': {pricing.CENTS_STARTER}'),
        (': outsidemaindish,', f': {pricing.CENTS_MAIN_DISH}'),
        (': outsideextradish,', f': {pricing.CENTS_EXTRA_DISH}'),
        (': outsidethirddish,', f': {pricing.CENTS_THIRD_DISH}'),
        (': outsidemaindessert,', f': {pricing.CENTS_DESSERT}'),
        (': outsideextradessert,', f': {pricing.CENTS_DESSERT}')])),
             (('form', 'method', 'POST', 'class', 'container', 'id', 'reservation', 'action', 'add_unchecked_reservation.cgi'),
              (('input', 'type', 'hidden', 'name', 'csrf_token', 'value', csrf_token.token),),
              (('div', 'class', 'row'),
               (('label', 'for', 'name-field-id', 'class', 'col-xs-3'), 'Nom'),
               (('input', 'id', 'name-field-id', 'class', 'col-xs-9', 'type', 'text', 'name', 'name', 'required', 'required', 'minlength', '2'),)),
              (('div', 'class', 'row'),
               (('label', 'for', 'email-field-id', 'class', 'col-xs-3'), 'e-mail ou téléphone'),
               (('input', 'id', 'email-field-id', 'class', 'col-xs-9', 'type', 'text', 'name', 'email', 'minlength', '2', 'pattern', '^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$|^[0-9.\\/ \\-]+$'),)),
              (('div', 'class', 'row'),
               (('label', 'for', 'extraComment-field-id', 'class', 'col-xs-12'), 'Commentaire (p.ex. pour le placement si vous venez avec un autre groupe)')),
              (('div', 'class', 'row'),
               (('input', 'id', 'extraComment-field-id', 'class', 'col-xs-12', 'type', 'text', 'name', 'extraComment'),)),
              (('div', 'class', 'row'),
               (('label', 'for', 'places-field-id', 'class', 'col-xs-3'), 'Nombre de places'),
               (('input', 'id', 'places-field-id', 'class', 'col-xs-3', 'name', 'places', 'type', 'number', 'min', '1', 'max', '50', 'value', '1'),),
               (('label', 'for', 'date-field-id', 'class', 'col-xs-2'), 'Date'),
               (('input', 'id', 'date-field-id', 'class', 'col-xs-4', 'name', 'date', 'type', 'date', 'readonly', 'readonly', 'value', '2099-01-01'),)),
              (('div', 'class', 'row'),
               (('fieldset', 'class', 'col-md-4'),
               ('legend', 'Menu Complet'),
               make_sum_group("inside-menu-starter",
                              "starter sum-group",
                              "Le nombre total d'entrées doit correspondre au nombre total de plats",
                              [('insidemainstarter', MAIN_STARTER),
                               ('insideextrastarter', EXTRA_STARTER)]),
               make_sum_group("inside-menu-dish",
                              "dish sum-group",
                              None,
                              [('insidemaindish', MAIN_DISH),
                               ('insideextradish', EXTRA_DISH),
                               ('insidethirddish', THIRD_DISH)]),
               make_sum_group("inside-menu-dessert",
                              "dessert sum-group",
                              "Le nombre total de desserts doit correspondre au nombre total de plats",
                              [('insidemaindessert', MAIN_DESSERT),
                               ('insideextradessert', EXTRA_DESSERT)])),
              (('fieldset', 'class', 'col-md-4'),
               ('legend', 'Menu Enfant'),
               make_sum_group("kids-menu-dish",
                              "dish sum-group",
                              None,
                              [('kidsmaindish', KIDS_MAIN_DISH),
                               ('kidsextradish', KIDS_EXTRA_DISH),
                               ('kidsthirddish', KIDS_THIRD_DISH)]),
               make_sum_group("kids-menu-dessert",
                              "dessert sum-group",
                              "Le nombre total de desserts doit correspondre au nombre total de plats enfants",
                              [('kidsmaindessert', MAIN_DESSERT),
                               ('kidsextradessert', EXTRA_DESSERT)])),
              (('fieldset', 'class', 'col-md-4'),
               ('legend', 'À la carte'),
               make_sum_group("outside-menu-starter",
                              "starter sum-group",
                              None,
                              [('outsidemainstarter', MAIN_STARTER),
                               ('outsideextrastarter', EXTRA_STARTER)]),
               make_sum_group("outside-menu-dish",
                              "dish sum-group",
                              None,
                              [('outsidemaindish', MAIN_DISH),
                               ('outsideextradish', EXTRA_DISH),
                               ('outsidethirddish', THIRD_DISH)]),
               make_sum_group("outside-menu-dessert",
                              "dessert sum-group",
                              None,
                              [('outsidemaindessert', MAIN_DESSERT),
                               ('outsideextradessert', EXTRA_DESSERT)]))),
              (('div', 'class', 'row'),
               (('p', 'class', 'col-md-12'),
                "La Société Royale d'Harmonie de Braine-l'Alleud respecte votre vie privée. Les données de contact que vous nous communiquez dans ce formulaire seront uniquement utilisées dans le cadre de ce souper italien, à moins que vous nous donniez l'autorisation de les garder pour vous informer de nos concerts et autres fêtes dans le futur. Contactez ", (('a', 'href', f"mailto:{INFO_EMAIL}"), INFO_EMAIL), " pour demander d'être retiré de nos fichiers.")),
              (('div', 'class', 'row'),
               (('input', 'type', 'checkbox', 'value', '', 'id', 'gdpr_accepts_use', 'name', 'gdpr_accepts_use', 'class', 'col-xs-1'),),
               (('label', 'for', 'gdpr_accepts_use', 'class', 'col-xs-11'), "Je désire être tenu au courant des activités futures de la SRH de Braine-l'Alleud et l'autorise à conserver mon nom et mon adresse email à cette fin.")),
              (('input', 'type', "submit", 'id', 'reservation-submit', 'value', "Confirmer", 'style', "width: 100%;"),)),
             ('hr',),
             ('ul',
              ('li', (('a', 'href', 'list_payments.cgi'), 'Gérer les paiements')),
              ('li', (('a', 'href', 'generate_tickets.cgi'), 'Générer les tickets nourriture pour impression'))))))
    except Exception:
        if print_content_type('text/html; charset=utf-8'):
            print()
        cgitb.handler()
