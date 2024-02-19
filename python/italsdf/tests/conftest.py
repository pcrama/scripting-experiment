try:
    from app.storage import Payment, Reservation
except ImportError:
    import sys_path_hack
    with sys_path_hack.app_in_path():
        from storage import Payment, Reservation


def make_reservation(**overrides) -> Reservation:
    defaults = dict(
        name='testing',
        email='test@example.com',
        extra_comment='unit test extra comment',
        places=0,
        date='2022-03-19',
        outside_extra_starter=0,
        outside_main_starter=0,
        outside_main_dish=0,
        outside_extra_dish=0,
        outside_third_dish=0,
        outside_main_dessert=0,
        outside_extra_dessert=0,
        inside_extra_starter=0,
        inside_main_starter=0,
        inside_main_dish=0,
        inside_extra_dish=0,
        inside_third_dish=0,
        inside_main_dessert=0,
        inside_extra_dessert=0,
        kids_main_dish=0,
        kids_extra_dish=0,
        kids_third_dish=0,
        kids_main_dessert=0,
        kids_extra_dessert=0,
        gdpr_accepts_use=True,
        cents_due=1253,
        bank_id="12349876",
        uuid='deadbeef',
        time=12345678.9,
        active=True,
        origin='unit tests')
    defaults.update(**overrides)
    reservation, tail = Reservation.parse_from_row(
        [defaults['name'],
         defaults['email'],
         defaults['extra_comment'],
         defaults['places'],
         defaults['date'],
         defaults['outside_main_starter'],
         defaults['outside_extra_starter'],
         defaults['outside_main_dish'],
         defaults['outside_extra_dish'],
         defaults['outside_third_dish'],
         defaults['outside_main_dessert'],
         defaults['outside_extra_dessert'],
         defaults['inside_main_starter'],
         defaults['inside_extra_starter'],
         defaults['inside_main_dish'],
         defaults['inside_extra_dish'],
         defaults['inside_third_dish'],
         defaults['inside_main_dessert'],
         defaults['inside_extra_dessert'],
         defaults['kids_main_dish'],
         defaults['kids_extra_dish'],
         defaults['kids_third_dish'],
         defaults['kids_main_dessert'],
         defaults['kids_extra_dessert'],
         defaults['gdpr_accepts_use'],
         defaults['cents_due'],
         defaults['bank_id'],
         defaults['uuid'],
         defaults['time'],
         defaults['active'],
         defaults['origin']])
    if not reservation or tail:
        raise RuntimeError("Unable to create test Reservation object")
    return reservation


def make_payment(**overrides) -> Payment:
    defaults = dict(
        rowid=None,
        timestamp=1705525636,
        amount_in_cents=3000,
        comment="unit test comment",
        uuid="c0ffee00beef1234",
        src_id="2023-1000",
        other_account="BE0101",
        other_name="Ms Abc",
        status="Accepté",
        user="unit-test-user",
        ip="1.2.3.4",
        confirmation_timestamp=None)
    defaults.update(**overrides)
    return Payment(**defaults)
