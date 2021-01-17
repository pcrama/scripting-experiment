def align_columns(pattern_prefix, pattern, columns):
    '''Align columns with given pattern if possible

    >>> align_columns('# ', 'ab cd ef', ['ab', 'c', 'ef'])
    'ab   c  ef'
    >>> align_columns('# ', 'ab cd ef', ['ab', 'cdcdcd', 'ef'])
    'ab   cdcdcd ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'c', 'ef'])
    'ab       c      ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd', 'ef'])
    'ab       cdcdcd ef'
    >>> align_columns('# ', 'ab     cd  ef', ['ab', 'cdcdcd', 'ef'])
    'ab       cdcdcd ef'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd', 'ef', 'gh', 'ijk'])
    'ab       cdcdcd ef gh ijk'
    >>> align_columns('# ', 'ab     cd     ef', ['ab', 'cdcdcd'])
    'ab       cdcdcd'
    >>> align_columns('# ', '   ab  cd     ef', ['ab', 'c', 'ef'])
    '     ab  c      ef'
    '''
    target_columns = []
    for column in get_target_columns(pattern):
        if column == 0:
            target_columns.append(0)
        else:
            target_columns.append(column + len(pattern_prefix))
    result = ''
    for data in columns:
        try:
            target = target_columns.pop(0)
        except IndexError:
            target = 0
        if result == '' and target == 0:
            result = data
            continue
        target = max(
            target,
            len(result) + 1 # at least one space between columns
        )
        result += ' ' * (target - len(result)) + data
    return result


def get_target_columns(pattern):
    '''List all indices where a new column start in a commented out line

    >>> get_target_columns('a    bc   def')
    [0, 5, 10]
    >>> get_target_columns('  a bc  def')
    [2, 4, 8]
    '''
    result = []
    idx = 0
    last_was_space = True
    while idx < len(pattern):
        if pattern[idx] in ' \t':
            last_was_space = True
        else:
            if last_was_space:
                result.append(idx)
            last_was_space = False
        idx += 1
    return result


def simple_test():
    input_text = [
        'Common            master            git.onespan.com/digipass/Common.git',
        'C_HsmIntfClasses  version/1.2.3     C_HsmIntfClasses',
        'SamLogin          version/2.0.3.4'
        ]
    PREFIX = '# '
    for line in input_text:
        print(f'{PREFIX}{line}')
        print(align_columns(PREFIX, line, [x if idx != 1 else '0123456789abcdefghijklmn' for (idx, x) in enumerate(line.split())]))
