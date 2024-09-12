# -*- coding: utf-8 -*-
'''Very limited HTML generation utilities.'''
import html
import sys
from typing import NoReturn


_html_gen_printed_header = False

def print_content_type(content_type, file=None):
    global _html_gen_printed_header
    if _html_gen_printed_header:
        return False
    print(f'Content-Type: {content_type}', file=file)
    _html_gen_printed_header = True
    return True


def format_bank_id(x):
    bank_id = ''.join(c for c in x if c.isdigit())
    if len(bank_id) != 12:
        return x
    return f'+++{bank_id[0:3]}/{bank_id[3:7]}/{bank_id[7:12]}+++'


def pluriel_naif(nombre, nom_et_pluriel):
    if isinstance(nom_et_pluriel, str):
        nom_et_pluriel = [nom_et_pluriel, f'{nom_et_pluriel}s']

    return f'1 {nom_et_pluriel[0]}' \
        if nombre == 1 \
        else f'{nombre} {nom_et_pluriel[1]}'


def cents_to_euro(cents):
    sign = '-' if cents < 0 else ''
    cents = abs(cents)
    return f'{sign}{cents // 100}.{cents % 100:02}'


def html_gen(data):
    def is_tuple(x):
        return type(x) is tuple
    if is_tuple(data) and len(data) == 2 and data[0] == 'raw':
        yield data[1]
    elif is_tuple(data):
        tag_name = None
        empty_elt = len(data) == 1
        for elt in data:
            if tag_name is None:
                tag = elt
                if is_tuple(tag):
                    tag_name = str(tag[0])
                    attr_values = []
                    for idx in range(1, len(tag), 2):
                        attr_values.append((tag[idx], html.escape(tag[idx + 1], quote=True)))
                    yield '<' + tag_name + ' ' + ' '.join(f'{x}="{y}"' for (x, y) in attr_values) + '>'
                else:
                    tag_name = str(tag)
                    yield f'<{tag_name}>'
                # https://developer.mozilla.org/en-US/docs/Glossary/Empty_element:
                empty_elt = tag_name.lower() in (
                    'area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                    'input', 'keygen', 'link', 'meta', 'param', 'source',
                    'track', 'wbr',)
            else:
                for x in html_gen(elt):
                    yield x
        if not empty_elt:
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
                        (('link', 'rel', 'stylesheet', 'href', 'https://www.srhbraine.be/css/bootstrap.min.css'),),
                        (('link', 'rel', 'stylesheet', 'href', 'https://cdn.jsdelivr.net/npm/remixicon@4.3.0/fonts/remixicon.css'),),
                        (('link', 'rel', 'stylesheet', 'href', 'https://www.srhbraine.be/css/app.css'),),
                        (('style',"""#home {background-image: url(https://www.srhbraine.be/images/fond-accueil--1.jpg); background-position: center; background-size: cover; filter: brightness(90%);}""")),),
                       ('body',
                        ("raw", '<!-- navbar -->'
                         '<nav id="navbar" class="navbar navbar-expand-lg bg-light fixed-top">'
                         '<div class="container">'
                         '<a class="navbar-brand" href="https://www.srhbraine.be/index.php"><img src="https://www.srhbraine.be/images/logo-srh.png" style="width: 90px;" alt="Responsive image">&nbsp;SRH</a>'
                         '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation"><span class="navbar-toggler-icon"></span></button>'
                         '<div class="collapse navbar-collapse" id="navbarNav">'
                         '<ul class="navbar-nav mx-auto">'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#home">Accueil</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#services">Qui sommes-nous ?</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#work">Galeries</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#sponsors">Sponsors</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/liens.php">Liens</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/agenda.php">Agenda</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#blog">Blog</a></li>'
                         '<li class="nav-item"><a class="nav-link" href="https://www.srhbraine.be/index.php#contact">Contact</a></li>'
                         '</ul>'
                         '<ul class="navbar-nav flex-row">'
                         '<li class="nav-item"><a class="social-icon" href="https://www.facebook.com/societeroyaleharmonie/" target="_blank"><i class="ri-facebook-line"></i></a></li>'
                         '<li class="nav-item"><a class="social-icon" href="https://www.instagram.com/srh_braine/" target="_blank"><i class="ri-instagram-line"></i></a></li>'
                         '<li class="nav-item"><a class="social-icon" href="https://www.youtube.com/@raphaeldagostino" target="_blank"><i class="ri-youtube-line"></i></a></li>'
                         '</ul></div></div></nav>'),
                        (('section', 'class', 'section-padding'),
                         (('div', 'class', 'container'),
                          (('div', 'class', 'row col-12'),
                           *body))),
                        (('section', 'class', 'section-padding row'),
                         (('footer', 'class', 'footer-bottom'),
                          (('div', 'class', 'container'),
                           (('div', 'class', 'row col-12'),
                            (('p', 'class', 'mb-0'),
                             'Retour au ',
                             (('a', 'href', 'https://www.srhbraine.be/'),
                              "site de la Société Royale d'Harmonie de Braine-l'Alleud"),
                             '.')))))))):
        yield x


def respond_html(data, file=None):
    if print_content_type('text/html; charset=utf-8', file=file):
        print('Content-Language: en, fr', file=file)
        print(file=file)
    for x in data:
        print(x, end='', file=file)


def redirect(new_url, and_exit=True, file=None):
    print('Status: 302', file=file)
    print(f'Location: {new_url}', file=file)
    print(file=file)
    if and_exit:
        sys.exit(0)

def redirect_to_event(suffix=None) -> NoReturn:
    suffix = f"#{suffix}" if suffix else ''
    redirect(f'https://srhbraine.be/{suffix}')
    sys.exit(0)
