import sys, threading, time

environment = {}
user_types = {}
user_functions = {}

class ReturnException(Exception):
    def __init__(self, value):
        super().__init__("ReturnException")
        self.value = value

class Token:
    def __init__(self, ttype, value):
        self.type = ttype
        self.value = value
    def __repr__(self):
        return "Token(" + str(self.type) + ", " + str(self.value) + ")"

class BreakException(Exception):
    pass

class ContinueException(Exception):
    pass

def tokenize(code):
    tokens = []
    i = 0
    while i < len(code):
        c = code[i]
        # 다중 행 주석 처리: /* ... */
        if c == '/' and i + 1 < len(code) and code[i + 1] == '*':
            i += 2
            while i < len(code) - 1:
                if code[i] == '*' and code[i + 1] == '/':
                    i += 2
                    break
                i += 1
            continue
        # 한 줄 주석 처리: // 또는 #
        if (c == '/' and i + 1 < len(code) and code[i + 1] == '/') or c == '#':
            while i < len(code) and code[i] != '\n':
                i += 1
            continue
        if c.isspace():
            i += 1
            continue
        # 식별자: 알파벳으로 시작, 이후 알파벳/숫자/언더스코어
        if c.isalpha():
            start = i
            while i < len(code) and (code[i].isalnum() or code[i]=='_'):
                i += 1
            word = code[start:i]
            tokens.append(Token("IDENT", word))
            continue
        # 숫자: 정수 또는 소수
        if c.isdigit():
            start = i
            dot_count = 0
            while i < len(code) and (code[i].isdigit() or code[i]=='.'):
                if code[i] == '.':
                    dot_count += 1
                i += 1
            num_str = code[start:i]
            if dot_count > 0:
                tokens.append(Token("NUMBER_FL", float(num_str)))
            else:
                tokens.append(Token("NUMBER_NUM", int(num_str)))
            continue
        # 문자열 (큰따옴표로 감싸진)
        if c == '"':
            i += 1
            start = i
            while i < len(code) and code[i] != '"':
                i += 1
            string_val = code[start:i]
            i += 1
            tokens.append(Token("STRING", string_val))
            continue
        # 세미콜론
        if c == ';':
            tokens.append(Token("SEMICOLON", ';'))
            i += 1
            continue
        # 기호: >, <, =, ! 등 (두 글자 연산자 포함)
        if c in ['>', '<', '=', '!']:
            if i + 1 < len(code) and code[i+1] == '=':
                tokens.append(Token("SYMBOL", c + '='))
                i += 2
                continue
            else:
                tokens.append(Token("SYMBOL", c))
                i += 1
                continue
        # 기타 기호: (, ), {, }, :, [, ], ,, .
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
        t = self.current_token()
        if t.type == "IDENT":
            if t.value == "use":
                return self.parse_use_stmt()
            if t.value == "newtype":
                return self.parse_newtype_stmt()
            if t.value == "func":
                return self.parse_func_decl()
            if t.value == "always":
                return self.parse_always_stmt()
            if t.value == "if":
                return self.parse_if_stmt()
            if t.value == "while":
                return self.parse_while_stmt()
            if t.value == "return":
                return self.parse_return_stmt()
            if t.value in ["break", "continue"]:
                self.advance()
                if self.current_token().type == "SEMICOLON":
                    self.advance()
                return (t.value + "_stmt",)
            # 변수 선언: type IDENT = ... 형태로 판단
            if (self.peek_token(1).type == "IDENT" and 
                self.peek_token(2).type == "SYMBOL" and 
                self.peek_token(2).value == '='):
                return self.parse_var_decl()
        return self.parse_expr_statement()

    def parse_use_stmt(self):
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '{':
            raise Exception("use 구문 오류: '{' 필요")
        self.advance()
        if self.current_token().type != "IDENT":
            raise Exception("use 구문 오류: 모듈 이름 필요")
        modname = self.current_token().value
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '}':
            raise Exception("use 구문 오류: '}' 필요")
        self.advance()
        if self.current_token().type == "SEMICOLON":
            self.advance()
        return ("use", modname)

    def parse_newtype_stmt(self):
        self.advance()
        if self.current_token().type != "IDENT":
            raise Exception("newtype 오류: 타입 이름 필요")
        tname = self.current_token().value
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
            raise Exception("newtype 오류: ':' 필요")
        self.advance()
        fields = []
        while True:
            tk = self.current_token()
            if tk.type == "IDENT" and tk.value == "end":
                if self.peek_token(1).type == "SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("newtype 오류: 'end;' 필요")
            ftok = self.current_token()
            if ftok.type != "IDENT":
                raise Exception("newtype 필드 오류: 타입 이름 필요")
            ftype = ftok.value
            self.advance()
            ftok2 = self.current_token()
            if ftok2.type != "IDENT":
                raise Exception("newtype 필드 오류: 필드 이름 필요")
            fname = ftok2.value
            self.advance()
            if self.current_token().type != "SEMICOLON":
                raise Exception("newtype 필드 오류: ';' 필요")
            self.advance()
            fields.append((ftype, fname))
        return ("newtype", tname, fields)

    def parse_func_decl(self):
        self.advance()
        if self.current_token().type != "IDENT":
            raise Exception("함수 선언 오류: 함수 이름 필요")
        fname = self.current_token().value
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '(':
            raise Exception("함수 선언 오류: '(' 필요")
        self.advance()
        params = []
        if not (self.current_token().type == "SYMBOL" and self.current_token().value == ')'):
            while True:
                ptypeTok = self.current_token()
                if ptypeTok.type != "IDENT":
                    raise Exception("함수 선언 오류: 매개변수 타입 필요")
                ptype = ptypeTok.value
                self.advance()
                pnameTok = self.current_token()
                if pnameTok.type != "IDENT":
                    raise Exception("함수 선언 오류: 매개변수 이름 필요")
                pname = pnameTok.value
                self.advance()
                params.append((ptype, pname))
                if self.current_token().type == "SYMBOL" and self.current_token().value == ',':
                    self.advance()
                else:
                    break
        if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
            raise Exception("함수 선언 오류: ')' 필요")
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
            raise Exception("함수 선언 오류: ':' 필요")
        self.advance()
        body = []
        while True:
            t2 = self.current_token()
            if t2.type == "IDENT" and t2.value == "end":
                if self.peek_token(1).type == "SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("함수 선언 오류: 'end;' 필요")
            if t2.type == "EOF":
                raise Exception("함수 선언 오류: EOF")
            s2 = self.parse_statement()
            body.append(s2)
        return ("func_decl", fname, params, body)

    def parse_always_stmt(self):
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '(':
            raise Exception("always 오류: '(' 필요")
        self.advance()
        interval_expr = self.parse_expression()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
            raise Exception("always 오류: ')' 필요")
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
            raise Exception("always 오류: ':' 필요")
        self.advance()
        bstmts = []
        while True:
            t3 = self.current_token()
            if t3.type == "IDENT" and t3.value == "end":
                if self.peek_token(1).type == "SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("always 오류: 'end;' 필요")
            if t3.type == "EOF":
                raise Exception("always 오류: EOF")
            st3 = self.parse_statement()
            bstmts.append(st3)
        return ("always_block", interval_expr, bstmts)

    def parse_if_stmt(self):
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '(':
            raise Exception("if 오류: '(' 필요")
        self.advance()
        ifcond = self.parse_expression()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
            raise Exception("if 오류: ')' 필요")
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
            raise Exception("if 오류: ':' 필요")
        self.advance()
        ifblock = []
        while True:
            t4 = self.current_token()
            if t4.type == "IDENT" and t4.value in ["elif", "else", "end"]:
                break
            if t4.type == "EOF":
                raise Exception("if 오류: EOF")
            sb = self.parse_statement()
            ifblock.append(sb)
        elifs = []
        while self.current_token().type == "IDENT" and self.current_token().value == "elif":
            self.advance()
            if self.current_token().type != "SYMBOL" or self.current_token().value != '(':
                raise Exception("elif 오류: '(' 필요")
            self.advance()
            ec = self.parse_expression()
            if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
                raise Exception("elif 오류: ')' 필요")
            self.advance()
            if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
                raise Exception("elif 오류: ':' 필요")
            self.advance()
            eb = []
            while True:
                t5 = self.current_token()
                if t5.type == "IDENT" and t5.value in ["elif", "else", "end"]:
                    break
                if t5.type == "EOF":
                    raise Exception("elif 오류: EOF")
                s5 = self.parse_statement()
                eb.append(s5)
            elifs.append((ec, eb))
        elseb = None
        if self.current_token().type == "IDENT" and self.current_token().value == "else":
            self.advance()
            if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
                raise Exception("else 오류: ':' 필요")
            self.advance()
            elseb = []
            while True:
                t6 = self.current_token()
                if t6.type == "IDENT" and t6.value == "end":
                    break
                if t6.type == "EOF":
                    raise Exception("else 오류: EOF")
                s6 = self.parse_statement()
                elseb.append(s6)
        if self.current_token().type == "IDENT" and self.current_token().value == "end":
            if self.peek_token(1).type == "SEMICOLON":
                self.advance()
                self.advance()
            else:
                raise Exception("if 오류: 'end;' 필요")
        else:
            raise Exception("if 오류: 'end;' 필요")
        return ("if_stmt", ifcond, ifblock, elifs, elseb)

    def parse_while_stmt(self):
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '(':
            raise Exception("while 오류: '(' 필요")
        self.advance()
        cexpr = self.parse_expression()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
            raise Exception("while 오류: ')' 필요")
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != ':':
            raise Exception("while 오류: ':' 필요")
        self.advance()
        wstmts = []
        while True:
            tw = self.current_token()
            if tw.type == "IDENT" and tw.value == "end":
                if self.peek_token(1).type == "SEMICOLON":
                    self.advance()
                    self.advance()
                    break
                else:
                    raise Exception("while 오류: 'end;' 필요")
            if tw.type == "EOF":
                raise Exception("while 오류: EOF")
            sw = self.parse_statement()
            wstmts.append(sw)
        return ("while_stmt", cexpr, wstmts)

    def parse_return_stmt(self):
        self.advance()
        rexpr = self.parse_expression()
        if self.current_token().type != "SEMICOLON":
            raise Exception("return 오류: 세미콜론 ';' 필요")
        self.advance()
        return ("return_stmt", rexpr)

    def parse_var_decl(self):
        # 변수 선언: type IDENT = expression;
        vtype = self.current_token().value
        self.advance()
        if self.current_token().type != "IDENT":
            raise Exception("변수 선언 오류: 변수 이름 필요")
        vname = self.current_token().value
        self.advance()
        if self.current_token().type != "SYMBOL" or self.current_token().value != '=':
            raise Exception("변수 선언 오류: '=' 필요")
        self.advance()
        init = self.parse_expression()
        if self.current_token().type == "SEMICOLON":
            self.advance()
        else:
            raise Exception("변수 선언 오류: 세미콜론 ';' 필요")
        return ("var_decl", vtype, vname, init)

    def parse_expr_statement(self):
        e = self.parse_expression()
        if self.current_token().type == "SEMICOLON":
            self.advance()
        else:
            raise Exception("세미콜론 ';' 필요 in expr_statement")
        return ("expr_stmt", e)

    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        expr = self.parse_logical_or()
        if self.current_token().type == "SYMBOL" and self.current_token().value == '=':
            self.advance()
            rhs = self.parse_assignment()
            expr = ("assign", expr, rhs)
        return expr

    def parse_logical_or(self):
        expr = self.parse_logical_and()
        while self.current_token().type == "IDENT" and self.current_token().value == "or":
            self.advance()
            right = self.parse_logical_and()
            expr = ("binary", "or", expr, right)
        return expr

    def parse_logical_and(self):
        expr = self.parse_comparison()
        while self.current_token().type == "IDENT" and self.current_token().value == "and":
            self.advance()
            right = self.parse_comparison()
            expr = ("binary", "and", expr, right)
        return expr

    def parse_comparison(self):
        expr = self.parse_additive()
        while self.current_token().type == "SYMBOL" and self.current_token().value in ['>', '<', '>=', '<=', '==', '!=']:
            op = self.current_token().value
            self.advance()
            r = self.parse_additive()
            expr = ("binary", op, expr, r)
        return expr

    def parse_additive(self):
        expr = self.parse_multiplicative()
        while self.current_token().type == "SYMBOL" and self.current_token().value in ['+','-']:
            op = self.current_token().value
            self.advance()
            r = self.parse_multiplicative()
            expr = ("binary", op, expr, r)
        return expr

    def parse_multiplicative(self):
        expr = self.parse_unary()
        while self.current_token().type == "SYMBOL" and self.current_token().value in ['*', '/', '%']:
            op = self.current_token().value
            self.advance()
            r = self.parse_unary()
            expr = ("binary", op, expr, r)
        return expr

    def parse_unary(self):
        if ((self.current_token().type == "SYMBOL" and self.current_token().value in ['-', '+']) or 
            (self.current_token().type == "IDENT" and self.current_token().value == "not")):
            op = self.current_token().value
            self.advance()
            operand = self.parse_unary()
            return ("unary", op, operand)
        else:
            return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            t0 = self.current_token()
            if t0.type == "SYMBOL" and t0.value == '(':
                self.advance()
                args = []
                if not (self.current_token().type == "SYMBOL" and self.current_token().value == ')'):
                    while True:
                        arg = self.parse_expression()
                        args.append(arg)
                        if self.current_token().type == "SYMBOL" and self.current_token().value == ',':
                            self.advance()
                        else:
                            break
                if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
                    raise Exception("함수 호출 오류: ')' 필요")
                self.advance()
                expr = ("func_call", expr, args)
            elif t0.type == "SYMBOL" and t0.value == '.':
                self.advance()
                if self.current_token().type != "IDENT":
                    raise Exception("멤버 접근 오류: 식별자 필요")
                memb = self.current_token().value
                self.advance()
                t1 = self.current_token()
                if t1.type == "SYMBOL" and t1.value == '(':
                    self.advance()
                    margs = []
                    if not (self.current_token().type == "SYMBOL" and self.current_token().value == ')'):
                        while True:
                            aa = self.parse_expression()
                            margs.append(aa)
                            if self.current_token().type == "SYMBOL" and self.current_token().value == ',':
                                self.advance()
                            else:
                                break
                    if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
                        raise Exception("멤버 호출 오류: ')' 필요")
                    self.advance()
                    expr = ("member_call", expr, memb, margs)
                else:
                    expr = ("member_access", expr, memb)
            elif t0.type == "SYMBOL" and t0.value == '[':
                self.advance()
                idx_expr = self.parse_expression()
                if self.current_token().type != "SYMBOL" or self.current_token().value != ']':
                    raise Exception("인덱스 접근 오류: ']' 필요")
                self.advance()
                expr = ("index", expr, idx_expr)
            else:
                break
        return expr

    def parse_primary(self):
        tk = self.current_token()
        if tk.type == "IDENT" and tk.value in ["true", "false"]:
            self.advance()
            return ("literal", "BOOL", True if tk.value=="true" else False)
        if tk.type == "SYMBOL" and tk.value == '[':
            self.advance()
            arr = []
            if self.current_token().type == "SYMBOL" and self.current_token().value == ']':
                self.advance()
                return ("li", arr)
            while True:
                e2 = self.parse_expression()
                arr.append(e2)
                if self.current_token().type == "SYMBOL" and self.current_token().value == ',':
                    self.advance()
                elif self.current_token().type == "SYMBOL" and self.current_token().value == ']':
                    self.advance()
                    break
                else:
                    raise Exception("배열 리터럴 오류: ',' 또는 ']' 필요")
            return ("li", arr)
        if tk.type == "SYMBOL" and tk.value == '{':
            self.advance()
            rec = []
            if self.current_token().type == "SYMBOL" and self.current_token().value == '}':
                self.advance()
                return ("record", rec)
            while True:
                e3 = self.parse_expression()
                rec.append(e3)
                if self.current_token().type == "SYMBOL" and self.current_token().value == ',':
                    self.advance()
                elif self.current_token().type == "SYMBOL" and self.current_token().value == '}':
                    self.advance()
                    break
                else:
                    raise Exception("레코드 리터럴 오류: ',' 또는 '}' 필요")
            return ("record", rec)
        if tk.type in ["NUMBER_NUM", "NUMBER_FL", "STRING"]:
            self.advance()
            return ("literal", tk.type, tk.value)
        if tk.type == "IDENT":
            self.advance()
            return ("ident", tk.value)
        if tk.type == "SYMBOL" and tk.value == '(':
            self.advance()
            e4 = self.parse_expression()
            if self.current_token().type != "SYMBOL" or self.current_token().value != ')':
                raise Exception("괄호 오류: ')' 필요")
            self.advance()
            return e4
        raise Exception(("표현식 파싱 오류", tk))

def interpret(statements):
    for st in statements:
        exec_stmt(st)

def exec_stmt(stmt):
    global environment
    stype = stmt[0]
    if stype == "newtype":
        # newtype 구문 실행 시 user_types와 environment에 등록
        _, tname, fields = stmt
        user_types[tname] = {"fields": fields}
        environment[tname] = {"newtype": tname, "fields": fields}
        return
    elif stype == "func_decl":
        _, fn, ps, bd = stmt
        func_obj = ("function", ps, bd, environment.copy())
        user_functions[fn] = func_obj
        environment[fn] = func_obj
        return
    elif stype == "var_decl":
        _, vt, vn, init = stmt
        val = eval_expr(init)
        if vt == "num":
            val = int(val)
        elif vt == "fl":
            val = float(val)
        elif vt == "str":
            val = str(val)
        elif vt == "bool":
            val = bool(val)
        elif vt == "li":
            pass
        elif vt in user_types:
            fs = user_types[vt]["fields"]
            # 초기값이 리스트라면 record 리터럴로 간주하여 변환
            if isinstance(val, list):
                if len(val) != len(fs):
                    raise Exception(vt + " 타입 필드 수 불일치")
                rec = {}
                for ((ft, fnm), fv) in zip(fs, val):
                    rec[fnm] = fv
                val = rec
            # 이미 딕셔너리이면 그대로 사용
            elif isinstance(val, dict):
                pass
            else:
                raise Exception("레코드 초기값은 { ... } 형태로 작성해야 합니다.")
        else:
            raise Exception("알 수 없는 타입: " + vt)
        environment[vn] = val
        return
    elif stype == "use":
        _, mname = stmt
        fname = mname + ".sst"
        try:
            with open(fname, "r", encoding="utf-8") as f:
                mc = f.read()
        except Exception as e:
            raise Exception("파일 " + fname + " 읽기 실패: " + str(e))
        tks = tokenize(mc)
        p2 = Parser(tks)
        sms = p2.parse_program()
        backup = environment.copy()
        environment.clear()
        interpret(sms)
        mod_defs = environment.copy()
        environment.clear()
        environment.update(backup)
        environment[mname] = mod_defs
        return
    elif stype == "expr_stmt":
        eval_expr(stmt[1])
        return
    elif stype == "return_stmt":
        _, exr = stmt
        rv = eval_expr(exr)
        raise ReturnException(rv)
    elif stype == "if_stmt":
        _, ifc, ifb, elifs, elseb = stmt
        cval = eval_expr(ifc)
        if cval:
            for s1 in ifb:
                exec_stmt(s1)
        else:
            done = False
            for ccond, cblk in elifs:
                cc = eval_expr(ccond)
                if cc:
                    for s2 in cblk:
                        exec_stmt(s2)
                    done = True
                    break
            if not done and elseb is not None:
                for s3 in elseb:
                    exec_stmt(s3)
        return
    elif stype == "while_stmt":
        _, cexpr, wblk = stmt
        while True:
            condv = eval_expr(cexpr)
            if not condv:
                break
            try:
                for s4 in wblk:
                    exec_stmt(s4)
            except BreakException:
                break
            except ContinueException:
                continue
        return
    elif stype == "always_block":
        _, intex, b1 = stmt
        ival = eval_expr(intex)
        def loopf():
            while True:
                for s5 in b1:
                    exec_stmt(s5)
                time.sleep(ival)
        t = threading.Thread(target=loopf)
        t.daemon = True
        t.start()
        return
    elif stype == "break_stmt":
        raise BreakException()
    elif stype == "continue_stmt":
        raise ContinueException()
    else:
        pass

def eval_expr(expr):
    global environment
    etype = expr[0]
    if etype == "literal":
        _, tkt, val = expr
        return val
    elif etype == "ident":
        _, nm = expr
        if nm in environment:
            return environment[nm]
        else:
            raise Exception("정의되지 않은 식별자: " + nm)
    elif etype == "assign":
        _, lhs, rhs = expr
        if lhs[0] != "ident":
            raise Exception("할당 왼쪽은 식별자여야 합니다.")
        vn = lhs[1]
        v2 = eval_expr(rhs)
        environment[vn] = v2
        return v2
    elif etype == "unary":
        _, op, inr = expr
        rv = eval_expr(inr)
        if op == '-':
            return -rv
        elif op == '+':
            return +rv
        elif op == "not":
            return not rv
        else:
            raise Exception("알 수 없는 단항연산자: " + op)
    elif etype == "binary":
        _, op, le, re = expr
        lv = eval_expr(le)
        rv = eval_expr(re)
        if op == '+':
            return lv + rv
        elif op == '-':
            return lv - rv
        elif op == '*':
            return lv * rv
        elif op == '/':
            if isinstance(lv, int) and isinstance(rv, int):
                return lv // rv
            else:
                return lv / rv
        elif op == '%':
            return lv % rv
        elif op == '>':
            return lv > rv
        elif op == '<':
            return lv < rv
        elif op == '>=':
            return lv >= rv
        elif op == '<=':
            return lv <= rv
        elif op == '==':
            return lv == rv
        elif op == '!=':
            return lv != rv
        elif op == "or":
            return lv or rv
        elif op == "and":
            return lv and rv
        else:
            raise Exception("미지원 연산자: " + op)
    elif etype == "func_call":
        _, fx, argl = expr
        if fx[0] != "ident":
            raise Exception("함수 호출 오류: 이름은 식별자여야 합니다.")
        fn = fx[1]
        # 내장 함수 output, input, error 처리
        if fn == "output":
            vals = [eval_expr(a) for a in argl]
            print(" ".join(str(v) for v in vals))
            return None
        if fn == "input":
            ac = len(argl)
            if ac < 1:
                raise Exception("input에는 적어도 하나 이상의 변수 식별자가 필요합니다.")
            var_names = []
            for texpr in argl:
                if texpr[0] != "ident":
                    raise Exception("input 인자는 식별자여야 합니다.")
                var_names.append(texpr[1])
            needed = ac
            gathered = []
            while len(gathered) < needed:
                ln = sys.stdin.readline()
                if not ln:
                    raise Exception("입력 중단")
                parts = ln.strip().split()
                gathered.extend(parts)
            for i in range(ac):
                varn = var_names[i]
                rawv = gathered[i]
                if varn in environment:
                    oldv = environment[varn]
                    if isinstance(oldv, int):
                        newv = int(rawv)
                    elif isinstance(oldv, float):
                        newv = float(rawv)
                    elif isinstance(oldv, bool):
                        newv = (rawv.lower() in ["true", "1"])
                    else:
                        newv = rawv
                else:
                    newv = rawv
                environment[varn] = newv
            return None
        if fn == "error":
            vall = [eval_expr(a) for a in argl]
            msg = " ".join(str(v) for v in vall)
            raise Exception("Error: " + msg)
        # 내장 함수 exec 추가: 인자로 받은 문자열 코드를 실행
        if fn == "exec":
            if len(argl) != 1:
                raise Exception("exec 함수는 하나의 문자열 인자를 받아야 합니다.")
            code_str = eval_expr(argl[0])
            if not isinstance(code_str, str):
                raise Exception("exec 함수의 인자는 문자열이어야 합니다.")
            tokens = tokenize(code_str)
            parser = Parser(tokens)
            statements = parser.parse_program()
            interpret(statements)
            return None
        # 사용자 정의 함수 호출
        if fn not in user_functions:
            raise Exception("함수 정의 안됨: " + fn)
        finfo = user_functions[fn]
        fkind, fparams, fbody, fdefenv = finfo
        if fkind != "function":
            raise Exception("함수 아님: " + fn)
        if len(fparams) != len(argl):
            raise Exception("함수 호출 오류: 매개변수 수 불일치")
        localenv = fdefenv.copy()
        for (pt, pn), ax in zip(fparams, argl):
            av = eval_expr(ax)
            if pt == "num":
                av = int(av)
            elif pt == "fl":
                av = float(av)
            elif pt == "str":
                av = str(av)
            elif pt == "bool":
                av = bool(av)
            localenv[pn] = av
        bkup = environment.copy()
        environment.update(localenv)
        retv = None
        try:
            for stx in fbody:
                exec_stmt(stx)
        except ReturnException as rtx:
            retv = rtx.value
        environment = bkup
        return retv
    elif etype == "member_access":
        _, ox, mmb = expr
        obv = eval_expr(ox)
        if isinstance(obv, dict):
            if mmb in obv:
                return obv[mmb]
            else:
                raise Exception("레코드/객체에 필드 " + mmb + " 없음")
        else:
            raise Exception("멤버 접근 오류: 객체가 dict(레코드)가 아님")
    elif etype == "member_call":
        _, ox2, m2, ax2 = expr
        obj2 = eval_expr(ox2)
        a2 = [eval_expr(i) for i in ax2]
        if isinstance(obj2, dict):
            if m2 in obj2:
                func = obj2[m2]
                if isinstance(func, tuple) and func[0] == "function":
                    if len(func[1]) != len(a2):
                        raise Exception("멤버 함수 호출 오류: 매개변수 수 불일치")
                    localenv = func[3].copy()
                    for (ptype, pn), av in zip(func[1], a2):
                        if ptype == "num":
                            av = int(av)
                        elif ptype == "fl":
                            av = float(av)
                        elif ptype == "str":
                            av = str(av)
                        elif ptype == "bool":
                            av = bool(av)
                        localenv[pn] = av
                    backup = environment.copy()
                    environment.update(localenv)
                    retv = None
                    try:
                        for st in func[2]:
                            exec_stmt(st)
                    except ReturnException as rtx:
                        retv = rtx.value
                    environment = backup
                    return retv
                else:
                    raise Exception("멤버 호출 오류: " + m2 + "은 함수가 아님")
            else:
                raise Exception("모듈/레코드에 " + m2 + " 함수(멤버) 없음")
        if isinstance(obj2, str):
            if m2 == "size":
                if len(a2) > 0:
                    raise Exception("문자열 size()는 인자가 없어야 합니다.")
                return len(obj2)
            else:
                raise Exception("문자열에 정의되지 않은 메서드: " + m2)
        if isinstance(obj2, list):
            if m2 == "size":
                if len(a2) > 0:
                    raise Exception("리스트 size()는 인자가 없어야 합니다.")
                return len(obj2)
            raise Exception("리스트에 정의되지 않은 메서드: " + m2)
        if isinstance(obj2, tuple) and obj2[0] == "function":
            fkind, fparams, fbody, fdefenv = obj2
            if len(fparams) != len(a2):
                raise Exception("함수 호출 오류: 매개변수 수 불일치")
            localenv = fdefenv.copy()
            for (ptype, pn), av in zip(fparams, a2):
                if ptype == "num":
                    av = int(av)
                elif ptype == "fl":
                    av = float(av)
                elif ptype == "str":
                    av = str(av)
                elif ptype == "bool":
                    av = bool(av)
                localenv[pn] = av
            backup = environment.copy()
            environment.update(localenv)
            retv = None
            try:
                for st in fbody:
                    exec_stmt(st)
            except ReturnException as rtx:
                retv = rtx.value
            environment.clear()
            environment.update(backup)
            return retv
        raise Exception("멤버 호출 오류: 해당 객체 타입에서 메서드를 지원하지 않습니다.")
    elif etype == "index":
        _, base_expr, index_expr = expr
        base_val = eval_expr(base_expr)
        index_val = eval_expr(index_expr)
        try:
            return base_val[index_val]
        except Exception as e:
            raise Exception("인덱스 접근 오류: " + str(e))
    elif etype == "li":
        _, elms = expr
        return [eval_expr(e) for e in elms]
    elif etype == "record":
        _, els2 = expr
        return [eval_expr(e) for e in els2]
    else:
        raise Exception("알 수 없는 표현식 유형: " + str(etype))

if __name__ == "__main__":
    # 파일에서 읽지 않고, 내장 exec 기능을 테스트할 수 있습니다.
    with open('main.sst', 'r', encoding='utf-8') as f:
        code = f.read()
    tokens = tokenize(code)
    parser = Parser(tokens)
    statements = parser.parse_program()
    interpret(statements)
