#!/usr/bin/env python3

import re
import sys
from io import StringIO
from itertools import zip_longest

# TODO: v and # prefix parameters

# ~c : character
# ~% : newline
# ~& : freshline
# ~| : page feed (ignore)
# ~~ : tilde
# ~r : numbers, in many variants
# ~d : decimal integer
# ~b : binary integer
# ~o : octal integer
# ~x : hex integer
# ~f : fixed float
# ~e : exponential float
# ~g : general float
# ~$ : monetary float
# ~a : aesthetic
# ~s : standard (readable)
# ~w : write (maybe not applicable)
# ~_ : conditional newline
# ~< : logical block
# ~i : indent
# ~/ : call function
# ~t : tabulate
# ~< : justification
# ~> : end justfification
# ~* : goto
# ~[ : conditional expression
# ~] : end conditional expression
# ~{ : iteration
# ~} : end iteration
# ~? : recursive processing
# ~( : case conversion
# ~) : end case conversion
# ~p : plural
# ~; : clause separator
# ~^ : escape upward
# ~<newline> : ignored newline
# ~u : lost u directive https://gigamonkeys.wordpress.com/2010/10/07/lost-u-directive/



ends     = {'[':']', '{':'}', '(':')'}
arg_pat  = re.compile("(-?\d+)|('.)|()")
at_colon = re.compile('[:@]{0,2}')

classes = {}

def directive(char):
    def decorator(clazz):
        classes[char.lower()] = clazz
        return clazz
    return decorator

class Formatter:

    "Base class for formatters."

    def __init__(self, params, at, colon):
        self.params = params
        self.at     = at
        self.colon  = colon

    def __repr__(self):
        return '<{} {} at: {}; colon: {}>'.format(self.__class__.__name__, self.params, self.at, self.colon)

    def param(self, idx, default):
        return self.params[idx] if idx < len(self.params) else default

    def get_params(self, *defaults):
        return list(a or b for a, b in zip_longest(self.params, defaults))

    def emit(self, args, pos, newline, file):
        """
        Emit the appropriate text and return the new position in args
        and a boolean indicating whether the last character emitted
        was a newline.
        """
        raise Exception("Abstract method.")


class Text(Formatter):

    "Trivial formatter that emits literal text."

    def __init__(self, text):
        super().__init__([], False, False)
        self.text = text

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.text)

    def emit(self, args, pos, newline, file):
        print(self.text, end='', file=file)
        return pos, self.text[-1] == '\n'


@directive('c')
class Character(Formatter):

    "~c: character formatter"

    def emit(self, args, pos, newline, file):
        print(args[pos], end='', file=file)
        return pos + 1, args[pos] == '\n'


@directive('%')
class Newline(Formatter):

    "~% : newline formatter"

    def emit(self, args, pos, newline, file):
        times = self.get_params(1)[0]
        for i in range(times):
            print('', file=file)
        return pos, True


@directive('&')
class Freshline(Formatter):

    "~& : freshline"

    def emit(self, args, pos, newline, file):
        if not newline:
            print('', file=file)
        return pos, True


@directive('r')
class Number(Formatter):

    def emit(self, args, pos, newline, file):
        print(args[pos], end='', file=file)
        return pos + 1, False


@directive('d')
class Decimal(Formatter):

    def emit(self, args, pos, newline, file):
        n = args[pos]
        col, pad, comma, comma_int = self.get_params(0, ' ', ',', 3)
        sign = '-' if n < 0 else ('+' if self.at else '')
        base = sign + (commafy(n, comma, comma_int) if self.colon else repr(n))
        print_padded(base, col, pad, file)
        return pos + 1, False

@directive('a')
class Aesthetic(Formatter):

    def emit(self, args, pos, newline, file):
        print(str(args[pos]), end='', file=file)
        return pos + 1, False


@directive('s')
class Standard(Formatter):

    def emit(self, args, pos, newline, file):
        print(repr(args[pos]), end='', file=file)
        return pos + 1, False


@directive('(')
class CaseConversion(Formatter):
    """
    With no flags, every uppercase character is converted to the corresponding lowercase character.

    ~:( capitalizes all words, as if by string-capitalize.

    ~@( capitalizes just the first word and forces the rest to lower case.

    ~:@( converts every lowercase character to the corresponding uppercase character.
    """

    def __init__(self, params, at, colon, formatters):
        super().__init__(params, at, colon)
        self.formatters = formatters

    def emit(self, args, pos, newline, file):
        s, p, nl = emit(self.formatters, args, pos, newline, file=None)

        if not (self.at or self.colon):  s = s.lower()
        elif self.colon and not self.at: s = string_capitalize(s)
        elif self.at and not self.colon: s = s.capitalize()
        elif self.at and self.colon:     s = s.upper()

        print(s, end='', file=file)
        return p, nl


def print_padded(s, columns, pad_char, file):
    for i in range(columns - len(s)):
        print(pad_char, end='', file=file)
    print(s, end='', file=file)


def commafy(n, comma, comma_int):
    n = abs(n)
    e = 10 ** comma_int

    s = str(n % e)
    n = n // e
    while n > 0:
        s = str(n % e) + comma + s
        n = n // e
    return s

def string_capitalize(s):
    return ''.join(s.capitalize() if re.fullmatch(r'\w+', s) else s for s in re.split(r'([^\w])', s))

def format(spec, *args, **kwargs):
    s, _, _ = emit(parse_spec(spec, 0), args, 0, True, **kwargs)
    return s


def parse_spec(spec, pos, end=None):

    formatters = []
    p_start = pos
    p = pos
    while p < len(spec):
        c = spec[p]
        if c == '~':
            if p > p_start:
                formatters.append(Text(spec[p_start:p]))

            if p + 1 < len(spec) and spec[p + 1] == end:
                return formatters, p + 2
            else:
                formatter, p = parse_directive(spec, p + 1, end)
                p_start = p
                formatters.append(formatter)
        else:
            p += 1

    if p > p_start:
        formatters.append(Text(spec[p_start:p]))

    return formatters


def parse_directive(spec, pos, end):

    args, p      = parse_args(spec, pos)
    at, colon, p = parse_at_colon(spec, p)

    char = spec[p].lower()

    if char == '~':
        return Text('~'), p + 1
    elif char in '[{(':
        formatters, p = parse_spec(spec, p + 1, end=ends[char])
        return classes[char](args, at, colon, formatters), p
    elif char in ']})':
        raise Exception("Unexpected ~{}".char)
    else:
        return classes[char](args, at, colon), p + 1



def parse_args(spec, pos):
    "Read comma-delimited list of args."
    args = []
    p = pos
    while p < len(spec):
        m = arg_pat.match(spec, p)
        if m:
            if m.group(1):
                args.append(int(m.group(1)))
            elif m.group(2):
                args.append(m.group(2)[1])
            else:
                args.append(None)
            p = m.end()

        if spec[p] != ',':
            break
        else:
            p += 1
    return args, p


def parse_at_colon(spec, pos):
    m = at_colon.match(spec, pos)
    s = m.group(0)
    return '@' in s, ':' in s, m.end()


def emit(formatters, args, pos, newline, file=sys.stdout):
    string_output = file is None

    if string_output:
        file = StringIO()

    p, nl = pos, newline
    for f in formatters:
        p, nl = f.emit(args, p, nl, file)

    if string_output:
        text = file.getvalue()
        file.close()
        return text, p, nl
    else:
        return None, p, nl


if __name__ == '__main__':

    def check(spec, args, expected):
        out = format(spec, *args, file=None)
        if out != expected:
            print('FAIL: format("{}", {}) returned "{}" expected "{}"'.format(spec, args, out, expected))
        else:
            print('PASS: format("{}", {})'.format(spec, args))

    check('~&Hello', [], 'Hello')
    check('~%Hello', [], '\nHello')
    check('~a', [10], '10')
    check('~s', [10], '10')
    check('~(~a~)', ['The quick brown fox'], 'the quick brown fox')
    check('~:(~a~)', ['The quick brown fox'], 'The Quick Brown Fox')
    check('~@(~a~)', ['The quick brown fox'], 'The quick brown fox')
    check('~:@(~a~)', ['The quick brown fox'], 'THE QUICK BROWN FOX')
    check('~:d', [1234567], '1,234,567')
    check("~,,'.,4:d", [1234567], '123.4567')
    check("~2,'0d", [3], '03')
    check("~4,'0d-~2,'0d-~2,'0d", [2018, 6, 5], '2018-06-05')
    check("~10d", [123], "       123")
