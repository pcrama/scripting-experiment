import sys_path_hack

with sys_path_hack.app_in_path():
    import storage


def make_reservation(**overrides):
    defaults = dict(
        name='testing',
        email='test@example.com',
        extra_comment='unit test extra comment',
        places=0,
        date='2022-03-19',
        outside_extra_starter=0,
        outside_main_starter=0,
        outside_bolo=0,
        outside_extra_dish=0,
        outside_dessert=0,
        inside_extra_starter=0,
        inside_main_starter=0,
        inside_bolo=0,
        inside_extra_dish=0,
        kids_bolo=0,
        kids_extra_dish=0,
        gdpr_accepts_use=True,
        cents_due=1253,
        bank_id="12349876",
        uuid='deadbeef',
        time=12345678.9,
        active=True,
        origin='unit tests')
    defaults.update(**overrides)
    return storage.Reservation(**defaults)
