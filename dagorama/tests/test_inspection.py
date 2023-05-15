import pytest

from dagorama.inspection import verify_function_call


def test_fn(a, b, c=3):
    pass


def test_fn_2(a, b, c):
    pass


@pytest.mark.parametrize(
    "fn, calling_args, calling_kwargs, expected",
    [
        (test_fn, (1, 2), {}, True),  # should not raise any exception
        (test_fn, (1,), {"b": 2}, True),  # should not raise any exception
        (test_fn, (1,), {"b": 2, "d": 4}, TypeError),  # should raise TypeError
        (test_fn, (1,), {}, TypeError),  # should raise TypeError
        (test_fn_2, (1, 2), {}, TypeError),  # should raise TypeError
        (test_fn_2, (1, 2), {"c": 3}, True),  # should not raise any exception
    ],
)
def test_verify_function_call(fn, calling_args, calling_kwargs, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            verify_function_call(fn, calling_args, calling_kwargs)
    else:
        assert verify_function_call(fn, calling_args, calling_kwargs) == expected
