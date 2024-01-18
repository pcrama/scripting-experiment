import sys_path_hack

with sys_path_hack.app_in_path():
    from storage import Reservation, Payment


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
    return Reservation(**defaults)


def make_payment(**overrides):
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
        ip="1.2.3.4")
    defaults.update(**overrides)
    return Payment(**defaults)
