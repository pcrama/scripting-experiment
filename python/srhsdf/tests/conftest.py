try:
    from app.storage import Payment, Reservation
except ImportError:
    import sys_path_hack
    with sys_path_hack.app_in_path():
        from storage import Payment, Reservation


def make_reservation(**overrides) -> Reservation:
    defaults = dict(
        civility='',
        first_name='',
        last_name='testing',
        email='test@example.com',
        date='2024-11-30',
        paying_seats=2,
        free_seats=3,
        gdpr_accepts_use=True,
        cents_due=100,
        bank_id="12349876",
        uuid='deadbeef',
        timestamp=12345678.9,
        active=True,
        origin='unit tests')
    defaults.update(**overrides)
    reservation, tail = Reservation.parse_from_row(
        [defaults['civility'],
         defaults['first_name'],
         defaults['last_name'],
         defaults['email'],
         defaults['date'],
         defaults['paying_seats'],
         defaults['free_seats'],
         defaults['gdpr_accepts_use'],
         defaults['cents_due'],
         defaults['bank_id'],
         defaults['uuid'],
         defaults['timestamp'],
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
        bank_ref="202308081060",
        other_account="BE0101",
        other_name="Ms Abc",
        status="Accepté",
        user="unit-test-user",
        ip="1.2.3.4",
        confirmation_timestamp=None,
        active=True)
    defaults.update(**overrides)
    return Payment(**defaults)
