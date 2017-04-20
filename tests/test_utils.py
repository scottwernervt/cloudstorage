from cloudstorage.utils import rgetattr, rsetattr


def test_rgetattr():
    b = type('B', (), {'c': True})()
    a = type('A', (), {'b': b})()
    assert rgetattr(a, 'b.c')


def test_rsetattr():
    b = type('B', (), {'c': True})()
    a = type('A', (), {'b': b})()
    rsetattr(a, 'b.c', False)
    assert not a.b.c
