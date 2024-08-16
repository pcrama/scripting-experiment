# -*- coding: utf-8 -*-
'''Very limited HTML generation utilities.'''
import html
import sys


_html_gen_printed_header = False

def print_content_type(content_type):
    global _html_gen_printed_header
    if _html_gen_printed_header:
        return False
    print(f'Content-Type: {content_type}')
    _html_gen_printed_header = True
    return True


def format_bank_id(x):
    bank_id = ''.join(c for c in x if c.isdigit())
    if len(bank_id) != 12:
        return x
    return f'+++{bank_id[0:3]}/{bank_id[3:7]}/{bank_id[7:12]}+++'


def cents_to_euro(cents):
    return f'{cents // 100}.{cents % 100:02}'


def html_gen(data):
    def is_tuple(x):
        return type(x) is tuple
    if is_tuple(data):
        tag_name = None
        single_elt = len(data) == 1
        for elt in data:
            if tag_name is None:
                tag = elt
                if is_tuple(tag):
                    tag_name = str(tag[0])
                    attr_values = []
                    for idx in range(1, len(tag), 2):
                        attr_values.append((tag[idx], html.escape(tag[idx + 1], quote=True)))
                    yield '<' + tag_name + ' ' + ' '.join(f'{x}="{y}"' for (x, y) in attr_values)
                else:
                    tag_name = str(tag)
                    yield f'<{tag_name}'
                yield ('/>' if single_elt else '>')
            else:
                for x in html_gen(elt):
                    yield x
        if not single_elt:
            yield f'</{tag_name}>'
    else:
        yield html.escape(str(data), quote=False)


def html_document(title, body):
    yield '<!DOCTYPE HTML>'
    for x in html_gen((('html', 'lang', 'fr'),
                       ('head',
                        (('meta', 'charset', 'utf-8'),),
                        (('meta', 'name', 'viewport', 'content', 'width=device-width, initial-scale=1.0'),),
                        ('title', title),
                        (('link', 'rel', 'stylesheet', 'href', 'styles.css'),)),
                       ('body',
                        *body,
                        ('hr', ),
                        ('p',
                         'Retour au ',
                         (('a', 'href', 'https://www.srhbraine.be/'),
                          "site de la Société Royale d'Harmonie de Braine-l'Alleud"),
                         '.')))):
        yield x


def respond_html(data):
    if print_content_type('text/html; charset=utf-8'):
        print('Content-Language: en, fr')
        print()
    for x in data:
        print(x, end='')


def redirect(new_url, and_exit=True):
    print('Status: 302')
    print(f'Location: {new_url}')
    print()
    if and_exit:
        sys.exit(0)

def redirect_to_event():
    redirect('https://www.srhbraine.be/concert-de-gala-2022/')
