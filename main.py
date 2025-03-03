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

        if c == '/' and i + 1 < len(code) and code[i + 1] == '/':
            i += 2
            while i < len(code) and code[i] != '\n':
                i += 1
            continue

        if c == '#':
            while i < len(code) and code[i] != '\n':
                i += 1
            continue

        if c.isspace():
            i += 1
            continue

        if c.isalpha():
            start = i
            while i < len(code) and (code[i].isalnum() or code[i] == '_'):
                i += 1
            word = code[start:i]
            tokens.append(Token("IDENT", word))
            continue

        if c.isdigit():
            start = i
            dot_count = 0
            while i < len(code) and (code[i].isdigit() or code[i] == '.'):
                if code[i] == '.':
                    dot_count += 1
                i += 1
            num_str = code[start:i]
            if dot_count > 0:
                tokens.append(Token("NUMBER_FL", float(num_str)))
            else:
                tokens.append(Token("NUMBER_NUM", int(num_str)))
            continue

        if c == '"':
            i += 1
            start = i
            while i < len(code) and code[i] != '"':
                i += 1
            string_val = code[start:i]
            i += 1
            tokens.append(Token("STRING", string_val))
            continue

        if c == ';':
            tokens.append(Token("SEMICOLON", ';'))
            i += 1
            continue

        if c in ['>', '<', '=', '!']:
            if i + 1 < len(code) and code[i + 1] == '=':
                tokens.append(Token("SYMBOL", c + '='))
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
        t = self.current_token()
        if t.type == "IDENT" and t.value == "use":
            return self.parse_use_stmt()
        if t.type == "IDENT" and t.value == "newtype":
            return self.parse_newtype_stmt()
        if t.type == "IDENT" and t.value == "func":
            return self.parse_func_decl()
        if t.type == "IDENT" and t.value == "always":
            return self.parse_always_stmt()
        if t.type == "IDENT" and t.value == "if":
            return self.parse_if_stmt()
        if t.type == "IDENT" and t.value == "while":
            return self.parse_while_stmt()
        if t.type == "IDENT" and t.value == "return":
            return self.parse_return_stmt()
        if t.type == "IDENT" and t.value == "break":
            self.advance()
            if self.current_token().type == "SEMICOLON":
                self.advance()
            return ("break_stmt",)
        if t.type == "IDENT" and t.value == "continue":
            self.advance()
            if self.current_token().type == "SEMICOLON":
                self.advance()
            return ("continue_stmt",)
        if t.type == "IDENT" and (t.value in ["num", "fl", "str", "bool", "li"] or t.value in user_types):
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
        user_types[tname] = {"fields": fields}
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
            if t4.type == "IDENT" and t4.value in ["elif","else","end"]:
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
                if t5.type == "IDENT" and t5.value in ["elif","else","end"]:
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
        expr = self.parse_unary()  # parse_postfix() 대신 parse_unary() 호출
        while self.current_token().type == "SYMBOL" and self.current_token().value in ['*', '/', '%']:
            op = self.current_token().value
            self.advance()
            r = self.parse_unary()  # 동일하게 parse_unary() 사용
            expr = ("binary", op, expr, r)
        return expr

    def parse_unary(self):
        if (self.current_token().type == "SYMBOL" and self.current_token().value in ['-', '+']) or \
                (self.current_token().type == "IDENT" and self.current_token().value == "not"):
            op = self.current_token().value
            self.advance()
            operand = self.parse_unary()  # 연속된 단항 연산자 지원
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
        if tk.type == "IDENT" and tk.value in ["true","false"]:
            self.advance()
            return ("literal","BOOL", True if tk.value=="true" else False)
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
        if tk.type in ["NUMBER_NUM","NUMBER_FL","STRING"]:
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
        return
    elif stype == "func_decl":
        _, fn, ps, bd = stmt
        func_obj = ("function", ps, bd, environment.copy())
        user_functions[fn] = func_obj
        environment[fn] = func_obj  # 현재 환경에도 함수 저장
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
            if not isinstance(val, list):
                raise Exception("레코드 초기값은 { } 로 작성")
            if len(val) != len(fs):
                raise Exception(vt + " 타입 필드 수 불일치")
            rec = {}
            for ((ft, fnm), fv) in zip(fs, val):
                rec[fnm] = fv
            val = rec
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
                # continue: 현재 반복문의 나머지 코드를 건너뛰고 조건 평가로 돌아감
                pass
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
            raise Exception("할당 왼쪽은 식별자여야 함")
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
            raise Exception("함수 호출 오류: 이름은 식별자")
        fn = fx[1]
        if fn == "output":
            vals = [eval_expr(a) for a in argl]
            print(" ".join(str(v) for v in vals))
            return None
        if fn == "input":
            ac = len(argl)
            if ac < 1:
                raise Exception("input에는 변수 인자 필요")
            var_names = []
            for texpr in argl:
                if texpr[0] != "ident":
                    raise Exception("input 인자는 식별자")
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
                raise Exception("레코드에 필드 " + mmb + " 없음")
        else:
            raise Exception("멤버 접근: 객체가 레코드가 아님")


    elif etype == "member_call":
        _, ox2, m2, ax2 = expr
        obj2 = eval_expr(ox2)
        a2 = [eval_expr(i) for i in ax2]
        if isinstance(obj2, dict):
            if m2 in obj2:
                func = obj2[m2]
                if isinstance(func, tuple) and func[0] == "function":
                    if len(func[1]) != len(a2):
                        raise Exception("함수 호출 오류: 매개변수 수 불일치")
                    localenv = func[3].copy()  # fdefenv 복사
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
                    raise Exception("멤버 호출: " + m2 + "은 함수가 아님")
            else:
                raise Exception("모듈에 " + m2 + " 함수가 없음")
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
        if isinstance(obj2, str):
            if m2 == "size":
                if len(a2) > 0:
                    raise Exception("size() 인자 불필요")
                return len(obj2)
            else:
                raise Exception("문자열에 정의되지 않은 메서드: " + m2)
        if isinstance(obj2, list):
            if m2 == "size":
                if len(a2) > 0:
                    raise Exception("size() 인자 불필요")
                return len(obj2)
            raise Exception("리스트에 정의되지 않은 메서드: " + m2)
        raise Exception("멤버 호출: 객체가 지원되지 않음")

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
    f=open('main.sst','r')
    c1=f.readlines()
    code = ''
    for i in c1:
        code+=i
    tok = tokenize(code)
    par = Parser(tok)
    stm = par.parse_program()
    interpret(stm)
