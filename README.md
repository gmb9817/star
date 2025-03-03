# starscript
프로그래밍 언어 starscript를 만듭니다.

# 문법

변수 선언
변수는 타입 키워드와 함께 선언합니다. 지원하는 기본 타입은 정수(num), 실수(fl), 문자열(string), 불리언(bool), 리스트(li) 등이 있습니다.

```
num x=0;        // 정수 x를 선언합니다.

fl x=0.1;       // 실수 x를 선언합니다.

string x="hi";  // 문자열 x를 선언합니다.
```

함수
함수는 func 키워드를 사용하여 선언하며, 매개변수와 반환값을 지원합니다.
내부에서 return을 사용하여 값을 반환할 수 있습니다.

`func add(num a, num b) : 
    num result = a + b;
    return result;
end;`

함수 호출 예시:

`num sum = add(3, 5);
output(sum);  // 출력: 8`

제어 구조
조건문 (if, elif, else)
조건문은 if 구문을 사용하며, 선택적으로 elif와 else를 포함할 수 있습니다.

`if (x > 0) : 
    output("양수입니다");
elif (x == 0) : 
    output("제로입니다");
else : 
    output("음수입니다");
end;`

반복문 (while)
while 구문은 조건이 참일 동안 반복 실행됩니다.

`while (x < 10) : 
    output(x);
    x = x + 1;
end;`
반복문 내에서는 break와 continue를 사용하여 흐름을 제어할 수 있습니다.

사용자 정의 타입 (newtype)
newtype 키워드를 사용하여 사용자 정의 타입을 만들 수 있습니다.
타입 내 필드들을 정의하고, 이후 객체를 레코드 리터럴 방식으로 초기화합니다.

`newtype Person:
    string name;
    num age;
    end;`
    
사용 예시:

`Person p = {"Alice", 30};
output(p.name);  // 출력: Alice`

모듈 사용 (use)
다른 파일에 작성된 Starscript 코드를 모듈로 가져올 수 있습니다.
모듈은 use {모듈이름}; 형식으로 로드합니다.

`use {mymodule};`
모듈로 로드된 코드의 정의들은 현재 환경의 하위 모듈로 저장됩니다.

항상 실행 블록 (always)
always 블록은 주어진 간격마다 반복적으로 실행되는 코드를 정의합니다.
백그라운드 스레드에서 실행되므로 메인 프로그램 흐름에 영향을 주지 않습니다.

`always (1.0) : 
    output("1초마다 실행되는 코드");
end;`

배열 및 레코드
배열: 대괄호 []를 사용하여 배열 리터럴을 생성합니다.

`li numbers = [1, 2, 3, 4];
output(numbers.size());  // 출력: 4`

레코드: 중괄호 {}를 사용하여 레코드 리터럴을 생성합니다.
레코드는 newtype으로 선언한 타입에 맞게 필드를 채워야 합니다.

`Person p = {"Bob", 25};
output(p.age);  // 출력: 25`

주석
Starscript는 여러 스타일의 주석을 지원합니다.

한 줄 주석: // 또는 #
다중 행 주석: /* ... */

` // 이 코드는 x를 10으로 초기화합니다.
num x=10;

/* 
   다중 행 주석
   여러 줄에 걸쳐 작성할 수 있습니다.
*/ `

연산자
기본적인 산술, 비교, 논리 연산자를 지원합니다.

산술 연산자: +, -, *, /, %
비교 연산자: >, <, >=, <=, ==, !=
논리 연산자: and, or, not

`num a = 5;
num b = 3;
num sum = a + b;         // 덧셈
bool check = (a > b);    // 비교`

내장 함수
Starscript는 다음과 같은 내장 함수를 제공합니다.

output(x):
변수 x의 값을 출력합니다.

`output("Hello, World!");  // 출력: Hello, World!`

input(x):
변수 x의 값을 사용자로부터 입력 받습니다.

`str name="";
input(name);
output("입력된 이름: ", name);`

error(x):
오류 메시지를 출력하고 실행을 중단합니다.

`error("오류 발생: ", x);`

예제 코드
아래 예제는 Starscript의 다양한 기능을 종합적으로 보여줍니다.

```
// 변수 선언
num counter = 0;
string greeting = "Hello, Starscript!";

// 함수 정의
func increment(num value) :
    return value + 1;
end;

// 조건문과 반복문 사용
while (counter < 5) :
    output(greeting, " 카운터: ", counter);
    counter = increment(counter);
end;

// 사용자 정의 타입 및 레코드 사용
newtype Person:
    string name;
    num age;
end;

Person person = {"Alice", 28};
output("이름: ", person.name, ", 나이: ", person.age);

// 항상 실행 블록 (1초마다 실행)
always (1.0) :
    output("1초마다 실행되는 코드");
end;
```
