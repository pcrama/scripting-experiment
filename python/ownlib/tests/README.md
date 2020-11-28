# Tests #

## How to run tests ##

Run all tests with `all_tests.cmd`.  Note that the batch file makes certain assumptions about the directory layout.

## How to add tests ##

### Unit tests ###

Add your tests in this directory and update `__init__.py` to import all test cases so that they will be picked up automatically by `all_tests.cmd`.

### Doctests ###

Python expressions inside the documentation strings of all files directly rooted in the `ownlib` folder above this README.md file will be extracted by Python's `doctest` module and run.  See `..\dependencies_file.py` for examples.
