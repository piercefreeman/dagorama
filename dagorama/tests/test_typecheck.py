from inspect import getsourcelines
from tempfile import NamedTemporaryFile
from typing import no_type_check

from mypy import api as mypy_api


# This will be typechecked in a separate process
# We want it to create an error
@no_type_check
def logic_with_unnecessary_argument():
    from dagorama.definition import DAGDefinition, dagorama

    class CustomDag(DAGDefinition):
        @dagorama
        def entrypoint(self, number: int):
            self.linear_continue(number, 10)
            return number + 1

        def linear_continue(self, number: int):
            return number + 1


def test_unnecessary_argument_typecheck():
    with NamedTemporaryFile() as file:
        # Typechecking is static so we need to isolate our erroring code to a new file
        file.write(
            "\n".join(getsourcelines(logic_with_unnecessary_argument)[0]).encode()
        )
        file.seek(0)

        type_check_report, _, error_code = mypy_api.run([file.name])

    assert (
        'Too many arguments for "linear_continue" of "CustomDag"' in type_check_report
    )

    assert error_code == 1
