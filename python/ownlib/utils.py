'''Utilities'''

def print_header(s):
    '''Print a string with underlines below'''
    print(s)
    print('-' * len(s))


def pluralize(n, s):
    '''Concatenate a number and word turned to plural

    >>> pluralize(0, 'repository')
    '0 repositories'
    >>> pluralize(2, 'branch')
    '2 branches'
    >>> pluralize(3, 'tag')
    '3 tags'
    '''
    if n == 1:
        return f'1 {s}'
    else:
        if s.endswith('y'):
            plural = s[:-1] + 'ies'
        elif s.endswith('ch'):
            plural = s + 'es'
        else:
            plural = s + 's'
        return f'{n} {plural}'
