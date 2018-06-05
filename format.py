#!/usr/bin/env python3

import re
import sys
from io import StringIO

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
arg_pat  = re.compile("(-?\d+)|('.)")
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
        times = self.params[0] if self.params else 1
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


def format(spec, *args, **kwargs):
    return emit(parse_spec(spec, 0), args, **kwargs)


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
            args.append(int(m.group(1)) if m.group(1) else m.group(2)[1])
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


def emit(formatters, args, file=sys.stdout):
    string_output = file is None

    if string_output:
        file = StringIO()

    p, nl = 0, True
    for f in formatters:
        p, nl = f.emit(args, p, nl, file)

    if string_output:
        text = file.getvalue()
        file.close()
        return text
    else:
        return None




if __name__ == '__main__':

    format('~&Hello: ~a ~r~&', 'Peter', 10)
    exit()


    formatters = [
        Text('foo'),
        Character([], False, False),
        Newline([], False, False)
    ]
    args = ['a', 'bar']

    emit(formatters, args, sys.stdout)

    s = emit(formatters, args, None)
    print('text: {}'.format(s))
