import htmlgen

CENTS_STARTER = 800
CENTS_BOLO = 1000
CENTS_SCAMPIS = 1500
CENTS_DESSERT = 500
CENTS_MENU_BOLO = 2000
CENTS_MENU_SCAMPIS = 2500

def price_in_cents(r,
                   fondus=CENTS_STARTER,
                   assiettes=CENTS_STARTER,
                   bolo=CENTS_BOLO,
                   scampis=CENTS_SCAMPIS,
                   tiramisu=CENTS_DESSERT,
                   tranches=CENTS_DESSERT,
                   menu_bolo=CENTS_MENU_BOLO,
                   menu_scampis=CENTS_MENU_SCAMPIS):
    complete_menus = min([r.fondus + r.assiettes, r.bolo + r.scampis, r.tiramisu + r.tranches])
    if complete_menus == 0:
        correction = 0
    elif menu_bolo - bolo == menu_scampis - scampis and fondus == assiettes and tiramisu == tranches:
        correction = (fondus + bolo + tiramisu - menu_bolo) * complete_menus
    else:
        raise Exception("Unable to compute best price")
    return (
        r.fondus * fondus
        + r.assiettes * assiettes
        + r.bolo * bolo
        + r.scampis * scampis
        + r.tiramisu * tiramisu
        + r.tranches * tranches
        - correction)


def price_in_euros(r, **kwargs):
    cents = price_in_cents(r, **kwargs)
    return htmlgen.cents_to_euro(cents)
