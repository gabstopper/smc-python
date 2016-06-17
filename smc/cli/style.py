'''
Created on May 28, 2016

@author: davidlepage
'''

from pygments.token import Token
from pygments.util import ClassNotFound
from pygments.styles import get_style_by_name
from prompt_toolkit.styles import style_from_dict, default_style_extensions

class CustomizedStyle(object):

    def __init__(self, theme):
        self.style = self.style_factory(theme)

    def style_factory(self, theme):
           
        try:
            style = get_style_by_name(theme)
        except ClassNotFound:
            style = get_style_by_name('native')
    
        styles = {}
        styles.update(style.styles)
        styles.update(default_style_extensions)
        styles.update({
            Token.Menu.Completions.Completion.Current: 'bg:#00aaaa #000000',
            Token.Menu.Completions.Completion: 'bg:#008888 #ffffff',
            Token.Prompt: '#0066FF bold italic',
            Token.Name.Builtin: '#7401DF italic',
            Token.Literal.Number: '#424242 italic',
        })
    
        return style_from_dict(styles)