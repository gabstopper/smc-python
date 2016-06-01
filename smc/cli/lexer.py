
from pygments.lexer import RegexLexer
from pygments.lexer import words
from pygments.token import Keyword, Name, Literal

from options import all_option_names, all_arg_names, get_cmd

commands = get_cmd()
options = all_option_names()
args = all_arg_names()

class CommandLexer(RegexLexer):
    name = 'Command Lexer for smc cli'

    tokens = {
        'root': [
            (words(
                tuple(commands),
                prefix=r'\b',
                suffix=r'\b'),
             Keyword.Declaration),
            (words(
                tuple(options),
                prefix=r'\b',
                suffix=r'\b'),
             Name.Class),
            (words(
                tuple(args),
                prefix=r'\b',
                suffix=r'\b'),
             Name.Builtin),
             (r'.', Literal.Number)
        ]
    }
