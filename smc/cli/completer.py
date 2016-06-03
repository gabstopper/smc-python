from prompt_toolkit.completion import Completer, Completion
from options import get_cmd, get_cmd_target, sub_menus, split_command_and_args


class CommandCompleter(Completer):
    """ class implementing prompt-toolkit completer
    provides completion menu results, auto-completion and type matching 
    """
    def __init__(self, ignore_case=True):
        self.ignore_case = ignore_case
    
    def get_completions(self, document, complete_event):
    
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        words = CommandCompleter.get_tokens(document.text)
      
        command_name = split_command_and_args(words)[0]
        
        in_command = (len(words) > 1) and \
            (len(command_name.split(' ')) == 2)
        
        if in_command:
            
            previous_word = ''
            previous_start = document.find_start_of_previous_word(WORD=True)
            
            if previous_start == -len(word_before_cursor):
                previous_start = document.find_start_of_previous_word(
                    WORD=True, count=2)         
                
            if previous_start:
                previous_word = document.text_before_cursor[previous_start:]
                previous_word = previous_word.strip().split()[0]
               
            params = words[2:] if (len(words) > 1) else []
            
            collections = CommandCompleter.find_command_matches(command_name, 
                                                               word_before_cursor, 
                                                               previous_word,
                                                               params)
          
        else:
            if (document.text and not command_name) and not word_before_cursor : return [] #leading chars?
            menu_lst = get_cmd_target(command_name) if command_name else get_cmd()
            collections = CommandCompleter.find_matches(word_before_cursor,
                                                        menu_lst)

        return collections
    
            
    @staticmethod
    def find_command_matches(command, word='', prev='', params=[]):
        """ find matches in the context of a given command 
        :param command: two part command compiled before it reaches here
        :param word: chars typed
        :param prev: previous word seen
        :params params[]: list of args
        :return None
        """
        #print "Command:'%s', word: %s, prev: %s, params: %s" % (command, word, prev, params)     
        
        if command:                    
            top_cmd, sub_cmd = command.split(' ')
            if sub_cmd not in get_cmd_target(top_cmd) and not word:  #incorrect sub cmd
                return
                           
            if sub_cmd not in get_cmd_target(top_cmd): #verify target
                for name in sorted(get_cmd_target(top_cmd)):
                    if name.startswith(word) or not word:
                        yield Completion(name, -len(word))                   
                
            context_menu_items = sub_menus(top_cmd, sub_cmd) #menu's based on cmd and target context              
            unused_menu_items = [(name,meta) for (name,meta) in context_menu_items if name not in params]
            
            if [(x,y) for x,y in context_menu_items if x == prev] and prev != sub_cmd: #input
                return
            
            for menu, meta in unused_menu_items:  #return unused_menu_items
                if menu.startswith(word) or not word:
                    yield Completion(menu, -len(word), display_meta=meta)
                                  
    @staticmethod
    def find_matches(word, lst):
        """ find initial command and target match [cmd] [target]
        :param word searchable
        :param lst list to look for matches
        """
        word = word.lower()
        for name in sorted(lst):
            if name.startswith(word) or not word:
                    yield Completion(name, -len(word))
        
    @staticmethod
    def get_tokens(text):
        """ Parse out all tokens.
        :param text:
        :return: list
        """
        if text is not None:
            text = text.strip()
            return text.split(' ')
        return []