import argparse

def initialize_default_parser(description):
    """Build argparser with common options

    :param description: description of the script."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('starting_directory', type=str, nargs='?')
    return parser
