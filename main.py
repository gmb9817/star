import sys, threading, time

environment = {}
user_types = {}
user_functions = {}

class Token:
    def __init__(self, ttype, value):
        self.type = ttype
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, {self.value})"

def tokenize(code):
    tokens = []
    i = 0
    while i < len(code):
        c = code[i]
        if c.isspace():
            i += 1
            continue
        if c.isalpha():
            start = i
            while i < len(code) and (code[i].isalnum() or code[i]=='_'):
                i += 1
            word = code[start:i]
            tokens.append(Token("IDENT", word))
            continue
        if c.isdigit():
            start = i
            dot_count = 0
            while i < len(code) and (code[i].isdigit() or code[i]=='.'):
                if code[i]=='.':
                    dot_count += 1
                i += 1
            num_str = code[start:i]
            if dot_count > 0:
                tokens.append(Token("NUMBER_FL", float(num_str)))
            else:
                tokens.append(Token("NUMBER_NUM", int(num_str)))
            continue
        if c=='"':
            i += 1
            start = i
            while i < len(code) and code[i] != '"':
                i += 1
            string_val = code[start:i]
            i += 1
            tokens.append(Token("STRING", string_val))
            continue
        if c==';':
            tokens.append(Token("SEMICOLON", ';'))
            i += 1
            continue
        # 두 글자 연산자 처리
        if c in ['>', '<', '=', '!']:
            if i+1 < len(code) and code[i+1]=='=':
                tokens.append(Token("SYMBOL", c+'='))
                i += 2
                continue
            else:
                tokens.append(Token("SYMBOL", c))
                i += 1
                continue
        tokens.append(Token("SYMBOL", c))
        i += 1
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token("EOF", None)

    def advance(self):
        self.pos += 1

    def peek_token(self, offset=1):
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token("EOF", None)

    def parse_program(self):
        statements = []
        while self.current_token().type != "EOF":
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return statements

    def parse_statement(self):
        tk = self.current_token()
        if tk.type=="IDENT" and tk.value=="newtype":
            return self.parse_newtype_stmt()
        if tk.type=="IDENT" and tk.value=="func":
            return self.parse_func_decl()
        if tk.type=="IDENT" and tk.value=="always":
            return self.parse_always_stmt()
        if tk.type=="IDENT" and tk.value=="if":
            return self.parse_if_stmt()
        if tk.type=="IDENT" and tk.value=="while":
            return self.parse_while_stmt()
        if tk.type=="IDENT" and (tk.value in ["num","fl","str","bool","li"] or tk.value in user_types):
            return self.parse_var_decl()
        return self.parse_expr_statement()

    def parse_newtype_stmt(self):
        self.advance()
        if self.current_token().type != "IDENT":
            raise Exception("newtype 구문 오류: 타입 이름 필요")
        type_name = self.current_token().value
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
            raise Exception("newtype 구문 오류: ':' 필요")
        self.advance()
        fields = []
        while True:
            tk = self.current_token()
            if tk.type=="IDENT" and tk.value=="end":
                if self.peek_token(1).type=="SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("newtype 구문 오류: 'end;' 필요")
            field_type_token = self.current_token()
            if field_type_token.type!="IDENT":
                raise Exception("newtype 필드 오류: 타입 이름 필요")
            field_type = field_type_token.value
            self.advance()
            if self.current_token().type!="IDENT":
                raise Exception("newtype 필드 오류: 필드 이름 필요")
            field_name = self.current_token().value
            self.advance()
            if self.current_token().type!="SEMICOLON":
                raise Exception("newtype 필드 오류: ';' 필요")
            self.advance()
            fields.append((field_type, field_name))
        user_types[type_name] = {"fields": fields}
        return ("newtype", type_name, fields)

    def parse_var_decl(self):
        var_type = self.current_token().value
        self.advance()
        if self.current_token().type!="IDENT":
            raise Exception("변수 선언 오류: 변수 이름 필요")
        var_name = self.current_token().value
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!='=':
            raise Exception("변수 선언 오류: '=' 필요")
        self.advance()
        init_expr = self.parse_expression()
        if self.current_token().type=="SEMICOLON":
            self.advance()
        else:
            raise Exception("변수 선언 오류: 세미콜론 ';' 필요")
        return ("var_decl", var_type, var_name, init_expr)

    def parse_func_decl(self):
        self.advance()
        if self.current_token().type!="IDENT":
            raise Exception("함수 선언 오류: 함수 이름 필요")
        func_name = self.current_token().value
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!='(':
            raise Exception("함수 선언 오류: '(' 필요")
        self.advance()
        parameters = []
        if not (self.current_token().type=="SYMBOL" and self.current_token().value==')'):
            while True:
                if self.current_token().type!="IDENT":
                    raise Exception("함수 선언 오류: 매개변수 타입 필요")
                param_type = self.current_token().value
                self.advance()
                if self.current_token().type!="IDENT":
                    raise Exception("함수 선언 오류: 매개변수 이름 필요")
                param_name = self.current_token().value
                self.advance()
                parameters.append((param_type, param_name))
                if self.current_token().type=="SYMBOL" and self.current_token().value==',':
                    self.advance()
                else:
                    break
        if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
            raise Exception("함수 선언 오류: ')' 필요")
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
            raise Exception("함수 선언 오류: ':' 필요")
        self.advance()
        body_statements = []
        while True:
            if self.current_token().type=="IDENT" and self.current_token().value=="end":
                if self.peek_token(1).type=="SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("함수 선언 오류: 'end;' 필요")
            stmt = self.parse_statement()
            body_statements.append(stmt)
        return ("func_decl", func_name, parameters, body_statements)

    def parse_if_stmt(self):
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!='(':
            raise Exception("if 구문 오류: '(' 필요")
        self.advance()
        if_condition = self.parse_expression()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
            raise Exception("if 구문 오류: ')' 필요")
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
            raise Exception("if 구문 오류: ':' 필요")
        self.advance()
        if_block = []
        while True:
            tk = self.current_token()
            if tk.type=="IDENT" and tk.value in ["elif","else","end"]:
                break
            if tk.type=="EOF":
                raise Exception("if 구문 오류: 'end;' 없이 EOF")
            stmt = self.parse_statement()
            if_block.append(stmt)
        elif_clauses = []
        while self.current_token().type=="IDENT" and self.current_token().value=="elif":
            self.advance()
            if self.current_token().type!="SYMBOL" or self.current_token().value!='(':
                raise Exception("elif 구문 오류: '(' 필요")
            self.advance()
            elif_condition = self.parse_expression()
            if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
                raise Exception("elif 구문 오류: ')' 필요")
            self.advance()
            if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
                raise Exception("elif 구문 오류: ':' 필요")
            self.advance()
            elif_block = []
            while True:
                tk2 = self.current_token()
                if tk2.type=="IDENT" and tk2.value in ["elif","else","end"]:
                    break
                if tk2.type=="EOF":
                    raise Exception("elif 구문 오류: 'end;' 없이 EOF")
                stmt2 = self.parse_statement()
                elif_block.append(stmt2)
            elif_clauses.append((elif_condition, elif_block))
        else_block = None
        if self.current_token().type=="IDENT" and self.current_token().value=="else":
            self.advance()
            if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
                raise Exception("else 구문 오류: ':' 필요")
            self.advance()
            else_block = []
            while True:
                tk3 = self.current_token()
                if tk3.type=="IDENT" and tk3.value=="end":
                    break
                if tk3.type=="EOF":
                    raise Exception("else 구문 오류: 'end;' 없이 EOF")
                stmt3 = self.parse_statement()
                else_block.append(stmt3)
        if self.current_token().type=="IDENT" and self.current_token().value=="end":
            if self.peek_token(1).type=="SEMICOLON":
                self.advance()
                self.advance()
            else:
                raise Exception("if 구문 오류: 'end;' 필요")
        else:
            raise Exception("if 구문 오류: 'end;' 필요")
        return ("if_stmt", if_condition, if_block, elif_clauses, else_block)

    def parse_while_stmt(self):
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!='(':
            raise Exception("while 구문 오류: '(' 필요")
        self.advance()
        condition_expr = self.parse_expression()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
            raise Exception("while 구문 오류: ')' 필요")
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
            raise Exception("while 구문 오류: ':' 필요")
        self.advance()
        block_stmts = []
        while True:
            tk = self.current_token()
            if tk.type=="IDENT" and tk.value=="end":
                if self.peek_token(1).type=="SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("while 구문 오류: 'end;' 필요")
            if tk.type=="EOF":
                raise Exception("while 구문 오류: 'end;' 없이 EOF")
            stmt = self.parse_statement()
            block_stmts.append(stmt)
        return ("while_stmt", condition_expr, block_stmts)

    def parse_always_stmt(self):
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!='(':
            raise Exception("always 구문 오류: '(' 필요")
        self.advance()
        interval_expr = self.parse_expression()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
            raise Exception("always 구문 오류: ')' 필요")
        self.advance()
        if self.current_token().type!="SYMBOL" or self.current_token().value!=':':
            raise Exception("always 구문 오류: ':' 필요")
        self.advance()
        block_stmts = []
        while True:
            tk = self.current_token()
            if tk.type=="IDENT" and tk.value=="end":
                if self.peek_token(1).type=="SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("always 구문 오류: 'end;' 필요")
            if tk.type=="EOF":
                raise Exception("always 구문 오류: 'end;' 없이 EOF")
            stmt = self.parse_statement()
            block_stmts.append(stmt)
        return ("always_block", interval_expr, block_stmts)

    def parse_expr_statement(self):
        expr = self.parse_expression()
        if self.current_token().type=="SEMICOLON":
            self.advance()
        else:
            raise Exception("세미콜론 ';' 필요 in expr_statement")
        return ("expr_stmt", expr)

    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_comparison()
        if self.current_token().type=="SYMBOL" and self.current_token().value=='=':
            self.advance()
            rhs = self.parse_assignment()
            expr = ("assign", expr, rhs)
        return expr

    def parse_comparison(self):
        expr = self.parse_additive()
        while self.current_token().type=="SYMBOL" and self.current_token().value in ['>', '<', '>=', '<=', '==', '!=']:
            op = self.current_token().value
            self.advance()
            right = self.parse_additive()
            expr = ("binary", op, expr, right)
        return expr

    def parse_additive(self):
        expr = self.parse_multiplicative()
        while self.current_token().type=="SYMBOL" and self.current_token().value in ['+','-']:
            op = self.current_token().value
            self.advance()
            right = self.parse_multiplicative()
            expr = ("binary", op, expr, right)
        return expr

    def parse_multiplicative(self):
        expr = self.parse_postfix()
        while self.current_token().type=="SYMBOL" and self.current_token().value in ['*','/']:
            op = self.current_token().value
            self.advance()
            right = self.parse_postfix()
            expr = ("binary", op, expr, right)
        return expr

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            tk = self.current_token()
            if tk.type=="SYMBOL" and tk.value=='(':
                self.advance()
                args = []
                if not (self.current_token().type=="SYMBOL" and self.current_token().value==')'):
                    while True:
                        arg = self.parse_expression()
                        args.append(arg)
                        if self.current_token().type=="SYMBOL" and self.current_token().value==',':
                            self.advance()
                        else:
                            break
                if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
                    raise Exception("함수 호출 오류: ')' 필요")
                self.advance()
                expr = ("func_call", expr, args)
            elif tk.type=="SYMBOL" and tk.value=='.':
                self.advance()
                if self.current_token().type!="IDENT":
                    raise Exception("멤버 접근 오류: 식별자 필요")
                member_name = self.current_token().value
                self.advance()
                tk2 = self.current_token()
                if tk2.type=="SYMBOL" and tk2.value=='(':
                    self.advance()
                    args = []
                    if not (self.current_token().type=="SYMBOL" and self.current_token().value==')'):
                        while True:
                            arg = self.parse_expression()
                            args.append(arg)
                            if self.current_token().type=="SYMBOL" and self.current_token().value==',':
                                self.advance()
                            else:
                                break
                    if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
                        raise Exception("멤버 호출 오류: ')' 필요")
                    self.advance()
                    expr = ("member_call", expr, member_name, args)
                else:
                    expr = ("member_access", expr, member_name)
            else:
                break
        return expr

    def parse_primary(self):
        tk = self.current_token()
        if tk.type=="IDENT" and tk.value in ["true","false"]:
            self.advance()
            return ("literal", "BOOL", True if tk.value=="true" else False)
        if tk.type=="SYMBOL" and tk.value=='[':
            self.advance()
            elements = []
            if self.current_token().type=="SYMBOL" and self.current_token().value==']':
                self.advance()
                return ("li", elements)
            while True:
                elem = self.parse_expression()
                elements.append(elem)
                if self.current_token().type=="SYMBOL" and self.current_token().value==',':
                    self.advance()
                elif self.current_token().type=="SYMBOL" and self.current_token().value==']':
                    self.advance()
                    break
                else:
                    raise Exception("배열 리터럴 오류: ',' 또는 ']' 필요")
            return ("li", elements)
        if tk.type=="SYMBOL" and tk.value=='{':
            self.advance()
            elements = []
            if self.current_token().type=="SYMBOL" and self.current_token().value=='}':
                self.advance()
                return ("record", elements)
            while True:
                elem = self.parse_expression()
                elements.append(elem)
                if self.current_token().type=="SYMBOL" and self.current_token().value==',':
                    self.advance()
                elif self.current_token().type=="SYMBOL" and self.current_token().value=='}':
                    self.advance()
                    break
                else:
                    raise Exception("레코드 리터럴 오류: ',' 또는 '}' 필요")
            return ("record", elements)
        if tk.type in ["NUMBER_NUM","NUMBER_FL","STRING"]:
            self.advance()
            return ("literal", tk.type, tk.value)
        if tk.type=="IDENT":
            self.advance()
            return ("ident", tk.value)
        if tk.type=="SYMBOL" and tk.value=='(':
            self.advance()
            expr = self.parse_expression()
            if self.current_token().type!="SYMBOL" or self.current_token().value!=')':
                raise Exception("괄호 오류: ')' 필요")
            self.advance()
            return expr
        raise Exception(("표현식 파싱 오류: 예상치 못한 토큰", tk))

def interpret(statements):
    for stmt in statements:
        exec_stmt(stmt)

def exec_stmt(stmt):
    global environment
    stype = stmt[0]
    if stype=="newtype":
        return
    elif stype=="func_decl":
        _, func_name, params, body = stmt
        user_functions[func_name] = ("function", params, body, environment.copy())
        return
    elif stype=="var_decl":
        _, var_type, var_name, init_expr = stmt
        value = eval_expr(init_expr)
        if var_type=="num":
            value = int(value)
        elif var_type=="fl":
            value = float(value)
        elif var_type=="str":
            value = str(value)
        elif var_type=="bool":
            value = bool(value)
        elif var_type=="li":
            pass
        elif var_type in user_types:
            fields = user_types[var_type]["fields"]
            if not isinstance(value, list):
                raise Exception("레코드 초기값은 { }로 작성되어야 합니다.")
            if len(value)!=len(fields):
                raise Exception(f"{var_type} 타입 필드 수와 초기값 개수가 일치하지 않습니다.")
            rec={}
            for ((ftype,fname),fval) in zip(fields,value):
                rec[fname]=fval
            value=rec
        else:
            raise Exception(f"알 수 없는 타입: {var_type}")
        environment[var_name]=value
        return
    elif stype=="expr_stmt":
        eval_expr(stmt[1])
    elif stype=="if_stmt":
        _, ifcond, ifblock, elifs, elseblock = stmt
        if eval_expr(ifcond):
            for s in ifblock:
                exec_stmt(s)
        else:
            done=False
            for cnd,blk in elifs:
                if eval_expr(cnd):
                    for s2 in blk:
                        exec_stmt(s2)
                    done=True
                    break
            if not done and elseblock is not None:
                for s3 in elseblock:
                    exec_stmt(s3)
        return
    elif stype=="while_stmt":
        _, condexpr, blockstmts = stmt
        while eval_expr(condexpr):
            for s in blockstmts:
                exec_stmt(s)
        return
    elif stype=="always_block":
        _, intervalexpr, block = stmt
        ival = eval_expr(intervalexpr)
        def loopfunc():
            while True:
                for st in block:
                    exec_stmt(st)
                time.sleep(ival)
        t=threading.Thread(target=loopfunc)
        t.daemon=True
        t.start()
        return
    else:
        print("알 수 없는 문장 유형:", stmt)

def eval_expr(expr):
    global environment
    etype = expr[0]
    if etype=="literal":
        _, tktype, tkval = expr
        return tkval
    elif etype=="ident":
        _, name = expr
        if name in environment:
            return environment[name]
        else:
            raise Exception(f"정의되지 않은 식별자: {name}")
    elif etype=="assign":
        _, lhs, rhs = expr
        if lhs[0] != "ident":
            raise Exception("할당의 왼쪽은 식별자여야 합니다")
        var_name = lhs[1]
        val = eval_expr(rhs)
        environment[var_name] = val
        return val
    elif etype=="binary":
        _, op, left, right = expr
        lval = eval_expr(left)
        rval = eval_expr(right)
        if op == '+':
            return lval + rval
        elif op == '-':
            return lval - rval
        elif op == '*':
            return lval * rval
        elif op == '/':
            # 두 피연산자가 모두 정수면 소숫점 내림을 적용하여 정수 나눗셈 수행
            if isinstance(lval, int) and isinstance(rval, int):
                return lval // rval
            else:
                return lval / rval
        elif op == '>':
            return lval > rval
        elif op == '<':
            return lval < rval
        elif op == '>=':
            return lval >= rval
        elif op == '<=':
            return lval <= rval
        elif op == '==':
            return lval == rval
        elif op == '!=':
            return lval != rval
        else:
            raise Exception(f"미지원 연산자: {op}")
    elif etype=="func_call":
        _, fexpr, argsexpr = expr
        if fexpr[0] != "ident":
            raise Exception("함수 호출 오류: 함수 이름은 식별자여야 합니다")
        fname = fexpr[1]
        if fname == "output":
            values = [eval_expr(a) for a in argsexpr]
            print(" ".join(str(v) for v in values))
            return None
        if fname == "input":
            return None
        if fname not in user_functions:
            raise Exception(f"정의되지 않은 함수: {fname}")
        _, params, body, defenv = user_functions[fname]
        if len(params) != len(argsexpr):
            raise Exception("함수 호출 오류: 매개변수 수 불일치")
        localenv = defenv.copy()
        for (ptype, pname), arg in zip(params, argsexpr):
            av = eval_expr(arg)
            if ptype == "num":
                av = int(av)
            elif ptype == "fl":
                av = float(av)
            elif ptype == "str":
                av = str(av)
            elif ptype == "bool":
                av = bool(av)
            localenv[pname] = av
        backup = environment.copy()
        environment.update(localenv)
        ret = None
        for st2 in body:
            ret = exec_stmt(st2)
        environment = backup
        return ret
    elif etype=="member_access":
        _, objexpr, memb = expr
        o = eval_expr(objexpr)
        if isinstance(o, dict):
            if memb in o:
                return o[memb]
            else:
                raise Exception(f"레코드에 필드 {memb}이 없습니다.")
        else:
            raise Exception("멤버 접근 오류: 객체가 레코드가 아닙니다.")
    elif etype=="member_call":
        _, objexpr, memb, argsexpr = expr
        o = eval_expr(objexpr)
        argvals = [eval_expr(a) for a in argsexpr]
        if isinstance(o, str):
            if memb == "size":
                if argvals:
                    raise Exception("size()는 인자를 받지 않음")
                return len(o)
            else:
                raise Exception(f"정의되지 않은 문자열 메서드: {memb}")
        raise Exception("멤버 호출 오류: 객체가 지원되지 않음")
    elif etype=="li":
        _, elems = expr
        return [eval_expr(e) for e in elems]
    elif etype=="record":
        _, elems = expr
        return [eval_expr(e) for e in elems]
    else:
        raise Exception("알 수 없는 표현식 유형", expr)

if __name__=="__main__":
    code = r"""
    
    """
    tokens = tokenize(code)
    print(tokens)
    parser = Parser(tokens)
    stmts = parser.parse_program()
    interpret(stmts)
    print("Done.")
    print("환경 =", environment)
