import ply.yacc as yacc
import sys
from lex7 import tokens
import re

"""
expr : ID | STR | num | list
num  : REAL | INT
list : ( seq )
seq  : ε | expr seq
"""

commands = []

class Var:
    def __init__(self, name, order, var_type):
        self.name = name
        self.order = order
        self.var_type = var_type
        self.value = None

class FUNC:
    def __init__(self,name,nargs,body,kind):
        self.name = name
        self.nargs = nargs
        self.body = body
        self.kind = kind

    def sub(self,vars):
        return [re.sub(rf'\#{i}',f'"{v}"',s)
                for i,v in enumerate(vars)
                for s in self.body
                ]

def is_id(p):
    return type(p) == str and p[0] != '"'

def is_str(p):
    return type(p) == str and p[0] == '"'

def is_var(p):
    return type(p) != list and p in parser.ids and type(parser.ids[p]) == Var

##########################################################################################
def push_rec(p,commands):
    parg = push(p)
    if parg:
        commands.append(parg)
    else:
        g_eval_expr(p,commands)

def push(p):
    t = type(p)
    if t == int:
        return f'PUSHI {p}'
    elif t == float:
        return f'PUSHF {p}'
    elif is_str(p):
        return f'PUSHS {p}'
    elif is_var(p):
        return push_l(parser.ids[p].order)
    else:
        return False

def push_l(p):
    return f'PUSHL {p}'


def write(p):
    if p == 'int':
        return f'WRITEI'
    elif p == 'float':
        return f'WRITEF'
    elif p == 'str':
        return f'WRITES'


def dup(p):
    return f'DUP {p}'


def push_l(p):
    return f'PUSHL {p}'


def push_g(p):
    return f'PUSHL {p}'


def push_n(p):
    return f'PUSHN {int(p)}'


def push_a(p):
    return f'PUSHA {p}'


def pop(n):
    return f'POP {n}'


def store_l(p):
    return f'STOREL {p}'


def jump(label):
    return f'JUMP {label}'


def jz(label):
    return f'JZ {label}'


CALL = 'CALL'
RETURN = 'RETURN'
MULT = 'MUL'
EQUAL = 'EQUAL'

##########################################################################################

def g_eval_expr(p,commands):
    """
    3 relevant cases:
        - subexpression
        - variable
        - primitive value
    """
    match p[0]:
        case 'decl':
            for pair in p[1:]:
                var_name = pair[0]
                var_type = pair[1]
                parser.ids[var_name] = Var(
                    var_name,
                    parser.global_vars,
                    var_type)
                if var_type == 'array':
                    parser.ids[var_name].end = parser.ids[var_name].order + \
                        int(pair[2]) - 1
                    parser.global_vars += int(pair[2])
                    commands.append(push_n(pair[2]))
                else:
                    parser.global_vars += 1
                    commands.append(push_n(1))
        case 'let':
            for pair in p[1:]:
                var_name = pair[0]
                var_value = pair[1]

                pcom = push(var_value)
                if pcom :
                    commands.append(pcom)
                else:
                    g_eval_expr(p[1],commands)
                commands.append(store_l(parser.ids[var_name].order))
        case 'aref':
            if type(p[1]) != list and p[1] in parser.ids and type(parser.ids[p[1]]) == Var:
                commands.append(push_l(parser.ids[p[1]].order + int(p[2])))
        case 'aset':
            commands.extend([push(p[3]), store_l(
                parser.ids[p[1]].order + int(p[2]))])
        case 'while':
            begin_while = 'l' + str(parser.label_count)
            parser.label_count += 1
            end_while = 'l' + str(parser.label_count)
            parser.label_count += 1
            commands.append(begin_while + ':')
            pcond = push(p[1])
            if pcond:
                commands.append(pcond)
            else:
                g_eval_expr(p[1],commands)
            commands.append(jz(end_while))
            pbody = push(p[2])
            if pbody:
                commands.append(pbody)
            else:
                g_eval_expr(p[2],commands)
            commands.append(jump(begin_while))
            commands.append(end_while + ':')
        case ('mul' | 'add' | 'sub' | 'div' |
              'fmul' | 'fadd' | 'fsub' | 'fdiv' | 'mod' |
              'inf' | 'infeq' | 'sup' | 'supeq'
              'finf' | 'finfeq' | 'fsup' | 'fsupeq'):
            for arg in p[1:]:
                parg = push(arg)
                if parg:
                    commands.append(parg)
                else:
                    g_eval_expr(arg,commands)
            commands.append(p[0].upper())
        case 'writei' | 'writef' | 'writes':
            pcom = push(p[1])
            if pcom:
                commands.append(pcom)
            else:
                g_eval_expr(p[1],pcom)
            commands.append(p[0].upper())
        case 'read':
            commands.append(p[0].upper())
        case 'case':
            pcond = push(p[1])
            if pcond:
                commands.append(pcond)
            else:
                g_eval_expr(p[1],commands)
            commands.append(dup(1))
            end_case = 'l' + str(parser.label_count + len(p[2:]))
            parser.label_count += 1
            for case0 in p[2:3]:
                expr1,expr2 = case0[0],case0[1]
                pval = push(expr1)
                if pval:
                    commands.append(pval)
                else:
                    g_eval_expr(expr1,commands)
                pcod = push(expr2)
                commands.append(EQUAL)
                next_case_label = 'l' + str(parser.label_count)
                parser.label_count += 1
                commands.append(jz(next_case_label))
                if pcod:
                    commands.append(pcod)
                else:
                    g_eval_expr(expr2,commands)
                commands.append(jump(end_case))
            for i,case0 in enumerate(p[3:]):
                expr1,expr2 = case0[0],case0[1]
                commands.append(next_case_label + ":")
                commands.append(dup(1))
                pval = push(expr1)
                if pval:
                    commands.append(pval)
                else:
                    g_eval_expr(expr1,commands)
                commands.append(EQUAL)
                next_case_label = 'l' + str(parser.label_count)
                parser.label_count += 1
                commands.append(jz(next_case_label))
                pcod = push(expr2)
                if pcod:
                    commands.append(pcod)
                else:
                    g_eval_expr(expr2,commands)
                if i != len(p[3:]) - 1:
                    commands.append(jump(end_case))
            commands.append(next_case_label + ':')
    return commands

##########################################################################################

def p_expr_ID(p):
    """expr : ID"""
    p[0] = p[1]
    print('p_expr_ID =',p[0])

def p_expr_STR(p):
    """expr : STR"""
    p[0] = p[1]
    print('p_expr_STR =',p[0])

def p_expr_INT(p):
    """expr : INT"""
    p[0] = int(p[1])
    print('p_expr_INT =',p[0])

def p_expr_REAL(p):
    """expr : REAL"""
    p[0] = float(p[1])
    print('p_expr_REAL =',p[0])

##########################################################################################

def p_expr_list(p):
    """expr : list"""
    p[0] = p[1]
    print('p_expr_list =', p[0])

# fim da expressao
def p_list(p):
    """list : LP seq RP"""
    p[0] = p[2]
    print('p_list =', p [2])

##########################################################################################

def p_seq(p):
    """seq : expr seq """
    p[0] = [p[1]] + p[2]
    print('p_seq =', [p[1]],'+',p[2])

def p_seq_empty(p):
    """seq : """
    p[0] = []

##########################################################################################

def p_error(p):
    print("Syntax error", p)
    parser.exito = False

##########################################################################################

parser = yacc.yacc()
parser.exito = True

##########################################################################################
class Object(object):
    pass

parser.funcs = {}
parser.stack = [commands]
parser.states = Object()
parser.states.decl = False
# where identifiers will be stored
parser.types = {'int', 'real', 'string'}
parser.functions = {'decl', 'while', 'let', 'defprim', 'defun'}
parser.ids = dict.fromkeys(parser.functions.union(parser.types))
parser.exito = True
parser.global_vars = 0
parser.label_count = 0
parser.label_count1 = 0
parser.label_count2 = 0
parser.local_vars = {}
parser.decls = []
parser.whilestack = []
parser.casestack = []
##########################################################################################

# fonte = ""
# for linha in sys.stdin:
#     fonte += linha
# parser.parse(fonte)

# print(g_eval_expr(['decl', ['x', 'int']],[]))
# print(g_eval_expr(['while', ['infeq', 'x', 3], ['let', ['x', ['add', 'x', 1]]]],[]))
print(g_eval_expr(['case', ['infeq', 1, 2], [3, ['add', 4, 5]], [6, ['sub', 7, 8]]],[]))

# if __name__ == "__main__":
#     text = ''
#     for line in sys.stdin:
#         match line:
#             case '_@_\n':
#                 print(commands)
#                 parser.parse(text)
#                 tok = parser.token()
#                 while tok:
#                     print(tok)
#                     tok = parser.token()
#                 text = ''
#             case _:
#                 text += line

if parser.exito:
    print("Parsing finished successfully!")
