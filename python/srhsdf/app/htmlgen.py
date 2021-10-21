# -*- coding: utf-8 -*-
'''Very limited HTML generation utilities.'''
import html
import sys

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
                    tag_name = str(elt[0])
                    attr_values = []
                    for idx in range(1, 2, len(tag)):
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
                        ('title', title)),
                       ('body', )
                       + body
                       + (('hr', ),
                          ('p',
                           'Retour au ',
                           (('a', 'href', 'https://www.srhbraine.be/'),
                            "site de la Société Royale d'Harmonie de Braine-l'Alleud"),
                           '.')))):
        yield x


def respond_html(data):
    print('Content-Type: text/html; charset=utf-8')
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
