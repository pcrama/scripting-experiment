import htmlgen


def price_in_cents(r,
                   fondus=800,
                   assiettes=800,
                   bolo=1500,
                   scampis=1800,
                   pannacotta=600,
                   tranches=600,
                   menu_bolo=2500,
                   menu_scampis=2800):
    complete_menus = min([r.fondus + r.assiettes, r.bolo + r.scampis, r.pannacotta + r.tranches])
    if complete_menus == 0:
        correction = 0
    elif menu_bolo - bolo == menu_scampis - scampis and fondus == assiettes and pannacotta == tranches:
        correction = (fondus + bolo + pannacotta - menu_bolo) * complete_menus
    else:
        raise Exception("Unable to compute best price")
    return (
        r.fondus * fondus
        + r.assiettes * assiettes
        + r.bolo * bolo
        + r.scampis * scampis
        + r.pannacotta * pannacotta
        + r.tranches * tranches
        - correction)


def price_in_euros(r, **kwargs):
    cents = price_in_cents(r, **kwargs)
    return htmlgen.cents_to_euro(cents)
