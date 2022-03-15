import itertools

from pricing import (price_in_euros)

def write_column_header_rows(writer):
    PLATS = ('Assiette', 'Fondu', 'Bolo', 'Scampi', 'Tiramisu', 'Tranche',)
    # Wrap iterator in `tuple' because we want to traverse it twice!
    DOTS = tuple(itertools.repeat('...', len(PLATS) - 1))
    writer.writerow(
        ('','',
         'À la carte', *DOTS,
         'Menu', *DOTS,
         '','','','','','',))
    writer.writerow(
        ('Nom', 'Places',
         *PLATS,
         *PLATS,
         'Total', 'Commentaire', 'Email', 'RGPD', 'Actif', 'Origine',))


def export_reservation(writer, x):
    if x.origin:
        comment = x.email
        email = ''
        gdpr_email = ''
    else:
        comment = ''
        email = x.email
        gdpr_email = x.email if x.gdpr_accepts_use else ''
    writer.writerow((
        x.name, x.places,
        x.outside_assiettes, x.outside_fondus,
        x.outside_bolo, x.outside_scampis,
        x.outside_tiramisu, x.outside_tranches,
        x.inside_assiettes, x.inside_fondus,
        x.inside_bolo, x.inside_scampis,
        x.inside_tiramisu, x.inside_tranches,
        price_in_euros(x),
        comment, email, gdpr_email, x.active, x.origin
    ))
