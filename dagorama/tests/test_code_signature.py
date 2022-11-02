from dagorama.code_signature import calculate_function_hash
from multiprocessing import Pool


def test_code_signature_basic():
    def fn1():
        print("Testing")

    def fn2():
        print("Testing")

    def fn3():
        print("Different Value")

    # Full equality of name matters
    assert calculate_function_hash(fn1) != calculate_function_hash(fn2)

    # Normalize the names
    fn2.__name__ = "fn1"
    fn3.__name__ = "fn1"
    assert calculate_function_hash(fn1) == calculate_function_hash(fn2)
    assert calculate_function_hash(fn1) != calculate_function_hash(fn3)


def test_code_signature_dependencies():
    def fn1():
        print("Testing")

    # Should minimally be different
    assert calculate_function_hash(fn1) != calculate_function_hash(fn1, include_package_versions=True)


def get_hash(_):
    def fn1():
        print("Testing")

    return calculate_function_hash(fn1)


def test_same_hash_across_sessions():
    """
    Ensure that our hashing technique is resillient to separate process launches. This is explicitly
    not true with the built-in hash function:
    https://docs.python.org/3/reference/datamodel.html#object.__hash__
    http://www.ocert.org/advisories/ocert-2011-003.html
    """

    with Pool(10) as pool:
        results = pool.map(get_hash, range(100))
        assert len(set(results)) == 1
