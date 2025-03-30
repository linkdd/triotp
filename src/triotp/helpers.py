from types import ModuleType

import inspect
import sys


def current_module() -> ModuleType:
    """
    This function should be called at the root of a module.

    :returns: The current module (similar to `__name__` for the current module name)

    .. code-block:: python
       :caption: Example

       from triotp.helpers import current_module

       __module__ = current_module()  # THIS WORKS


       def get_module():
           return current_module()  # THIS WON'T WORK
    """

    stack_frame = inspect.currentframe()

    while stack_frame:
        if stack_frame.f_code.co_name == "<module>":
            if stack_frame.f_code.co_filename != "<stdin>":
                caller_module = inspect.getmodule(stack_frame)

            else:
                caller_module = sys.modules["__main__"]

            if caller_module is not None:
                return caller_module

            break

        stack_frame = stack_frame.f_back

    raise RuntimeError("Unable to determine the current module.")
