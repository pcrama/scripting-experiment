module ParserTests

open NUnit.Framework
open life.interpreter.Parser

[<SetUp>]
let Setup () =
    ()

let callParse1 t = parse1 { text = t; index = 0 }

let doTestParse1ExpectingSucess(input, expected) =
    Assert.AreEqual(Parsed ({ text = input; index = input.Length }, expected),
                    callParse1 input)

[<Test>]
let TestParse1ExpectingSuccess () =
    doTestParse1ExpectingSucess("1234", Integer 1234)
    doTestParse1ExpectingSucess(" -1234", Integer -1234)
    // int is 32 bits: test boundaries (2**31 - 1) & -(2**31)
    doTestParse1ExpectingSucess("2147483647", Integer 2147483647)
    doTestParse1ExpectingSucess("-2147483648", Integer -2147483648)
    doTestParse1ExpectingSucess("(12)", Cons(Integer 12, Nil))
    doTestParse1ExpectingSucess("(1 2)", Cons(Integer 1, Cons(Integer 2, Nil)))
    doTestParse1ExpectingSucess(
        "(1 \"two\" three)",
        Cons(Integer 1, Cons(String "two", Cons(Symbol "three", Nil))))

[<Test>]
let TestParse1ExpectingFailure () =
    Assert.AreEqual(
        PError ("Unterminated list", { text = "(1"; index = 2 }),
        callParse1 "(1")
    Assert.AreEqual(
        PError ("Unterminated list", { text = "(1(2)"; index = 5 }),
        callParse1 "(1(2)")

[<Test>]
let TestParseListExpectingSuccess() =
    let doTest t e =
        Assert.AreEqual(
            Parsed ({ text = t; index = t.Length }, e),
            parseList { text = t; index = 0 } dnil)
    doTest ")" Nil
    doTest "1)" (Cons (Integer 1, Nil))
    doTest "())" (Cons (Nil, Nil))
    doTest "(((((()))))))"
           (Cons (Cons (Cons (Cons (Cons (Cons (Nil, Nil), Nil), Nil), Nil), Nil), Nil))
    doTest "1 \"two\" three)"
           (Cons (Integer 1, Cons (String "two", Cons (Symbol "three", Nil))))
    doTest "1 ; the number 1\n\"two\"; a string\n\n three; a symbol\n)"
           (Cons (Integer 1, Cons (String "two", Cons (Symbol "three", Nil))))

[<Test>]
let TestParseTokenizeNumberSuccess() =
    let doTest t i r =
        Assert.AreEqual(
            Token ({ text = t; index = i }, Literal (Integer r)),
            tokenizeNumber t.[0] { text = t; index = 1 })
    doTest "2147483647" 10 2147483647
    doTest "2147483647   " 10 2147483647
    doTest "+02147483647 " 12 2147483647
    doTest "-2147483647  " 11 -2147483647
    doTest "-2147483648  " 11 -2147483648

[<Test>]
let TestParseTokenizeNumberOverflow() =
    let doTest t i =
        Assert.AreEqual(
            TError ("Integer overflow", { text = t; index = i }),
            tokenizeNumber t.[0] { text = t; index = 1 })
    doTest "9999999999" 9
    doTest "2147483648" 9
    doTest "-2147483649" 10
