import htmlgen

CENTS_STARTER = 900
CENTS_BOLO = 1200
CENTS_SCAMPIS = 1700
CENTS_DESSERT = 600
CENTS_MENU_BOLO = 2500
CENTS_MENU_SCAMPIS = 3000

def price_in_cents(r,
                   outside_fondus=CENTS_STARTER,
                   outside_assiettes=CENTS_STARTER,
                   outside_bolo=CENTS_BOLO,
                   outside_scampis=CENTS_SCAMPIS,
                   outside_tiramisu=CENTS_DESSERT,
                   outside_tranches=CENTS_DESSERT,
                   inside_bolo=CENTS_MENU_BOLO,
                   inside_scampis=CENTS_MENU_SCAMPIS):
    # complete_menus = min([r.outside_fondus + r.outside_assiettes, r.outside_bolo + r.outside_scampis, r.outside_tiramisu + r.outside_tranches])
    # if complete_menus == 0:
    #     correction = 0
    # elif menu_bolo - outside_bolo == menu_scampis - outside_scampis and outside_fondus == outside_assiettes and outside_tiramisu == outside_tranches:
    #     correction = (outside_fondus + outside_bolo + outside_tiramisu - menu_bolo) * complete_menus
    # else:
    #     raise Exception("Unable to compute best price")
    return (
        r.outside_fondus * outside_fondus
        + r.outside_assiettes * outside_assiettes
        + r.outside_bolo * outside_bolo
        + r.outside_scampis * outside_scampis
        + r.outside_tiramisu * outside_tiramisu
        + r.outside_tranches * outside_tranches
        + r.inside_bolo * inside_bolo
        + r.inside_scampis * inside_scampis)


def price_in_euros(r, **kwargs):
    cents = price_in_cents(r, **kwargs)
    return htmlgen.cents_to_euro(cents)
