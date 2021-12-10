module CompilerTests

open NUnit.Framework
open life.interpreter.Parser
open life.interpreter.Compiler

[<SetUp>]
let Setup () =
    ()

let rec valueList = function
    | [] -> Nil
    | x::tail -> Cons (x, valueList tail)

[<TestCase("plus", 0, "")>]
[<TestCase("plus", 4, "4")>]
[<TestCase("plus", 8, "5 3")>]
[<TestCase("plus", 17, "9 6 2")>]
[<TestCase("minus", 0, "")>]
[<TestCase("minus", -4, "4")>]
[<TestCase("minus", 2, "5 3")>]
[<TestCase("minus", 1, "9 6 2")>]
[<TestCase("multiply", 1, "")>]
[<TestCase("multiply", 4, "4")>]
[<TestCase("multiply", 15, "5 3")>]
[<TestCase("multiply", 108, "9 6 2")>]
[<TestCase("divide", 1, "108 9 6 2")>]
[<TestCase("divide", 2, "10 5")>]
[<TestCase("divide", 2, "108 9 6")>]
[<TestCase("divide", 1, "108 2 9 6")>]
let TestCompileBinaryOp sym expected inputs =
    let form = (Symbol sym ::
                match inputs with
                    | "" -> []
                    | x -> x.Split() |> Seq.toList |> List.map (System.Int32.Parse >> Integer))
    let compiled = form |> valueList |> compile
    Assert.AreEqual(Integer expected, compiled [])

[<TestCase("plus", 8)>]
[<TestCase("multiply", 15)>]
[<TestCase("minus", 2)>]
let TestCompileEvaluationExpression1 (op, expected) =
    let form = valueList [Symbol op; Symbol "x"; Symbol "y"]
    let x = 5
    let y = 3
    let env = [("x", Integer x); ("y", Integer y)]
    let compiled = compile form
    Assert.AreEqual(Integer expected, compiled env)

[<Test>]
let TestCompileEvaluationExpression2 () =
    // x * (3 + y) === (* x (+ 3 y))
    let form = valueList [Symbol "multiply"; Symbol "x"; valueList [Symbol "plus"; Integer 3; Symbol "y"]]
    let x = 22
    let y = 7
    let env = [("x", Integer x); ("y", Integer y)]
    let compiled = compile form
    Assert.AreEqual(x * (3 + y) |> Integer, compiled env)
