num pi = 3.141592653589793;
num e = 2.718281828459045;

func abs(num x):
    if (x < 0):
        x = -x;
    end;
    output(x);
end;

func sqrt(num x):
    if (x < 0):
        error("음수에 대해 sqrt는 정의되지 않음");
    end;
    num guess = x / 2;
    while ( (guess*guess - x) > 0.000001 or (guess*guess - x) < -0.000001 ):
        guess = (guess + x/guess) / 2;
    end;
    output(guess);
end;

func pow(num base, num exp):
    if (exp < 0):
        error("음수 지수는 지원하지 않습니다.");
    end;

    num result = 1;

    while (exp > 0):
        num half = exp / 2; 
        if ((half * 2) == exp):
            base = base * base;
            exp = exp / 2;
        else:
            result = result * base;
            exp = exp - 1;
        end;
    end;

    output(result);
end;
