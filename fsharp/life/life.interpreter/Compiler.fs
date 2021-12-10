module life.interpreter.Compiler

// open System.Collections.Generic
open life.interpreter.Parser

let mapProperList f vs =
    let rec go acc xs =
        match xs with
            | Nil -> List.rev acc
            | Cons (x, tail) -> go (f x :: acc) tail
            | _ -> invalidArg "vs" "is not a proper list"
    go [] vs

let compileReturnConstant (v : Value) =
    let compiled _ = v
    compiled

let numericBinaryOperator f =
    let result x y =
        match (x, y) with
            | (Integer n, Integer m) -> f n m |> Integer
            | _ -> invalidArg "xy" "Type error: wanted a number"
    result

let rec lookup env symb =
    match env with
        | [] -> None
        | (s, v)::tail ->
            if s = symb
            then Some v
            else lookup tail symb

let rec primitives () = dict [
    "if", compileIf
    "plus", compileSymmetricBinaryOperator (Integer 0) ((fun acc x -> acc + x) |> numericBinaryOperator)
    "multiply", compileSymmetricBinaryOperator (Integer 1) ((fun acc x -> acc * x) |> numericBinaryOperator)
    "minus", compileMinusOrDiv 0 (fun a b -> a - b) (fun a b -> a + b)
    "divide", compileMinusOrDiv 1 (fun a b -> a / b) (fun a b -> a * b)
    ]

and compileEvalVariable sym =
    match sym with
        | Symbol symb ->
            let compiled env =
                match lookup env symb with
                    | Some v -> v
                    | None -> failwith $"Unbound symbol {symb}"
            compiled
        | _ -> invalidArg "sym" $"{sym} is not a variable access"

and compileIf form =
    match form with
        | Cons (Symbol "if", Cons (test, Cons (thenForm, x))) ->
            let elseCompiled = match x with
                                   | Nil -> compileReturnConstant Nil
                                   | Cons (elseForm, Nil) -> compile elseForm
                                   | _ -> invalidArg "form" "Syntax error in if"
            let thenCompiled = compile thenForm
            let testCompiled = compile test
            let ifCompiled env =
                match testCompiled env with
                    | Nil -> elseCompiled env
                    | _ -> thenCompiled env
            ifCompiled
        | _ -> invalidArg "form" "Syntax error in if"

and compile form =
    match form with
        | Symbol _ -> compileEvalVariable form
        | Integer _ -> compileReturnConstant form
        | Nil -> compileReturnConstant form
        | Cons (Symbol "quote", Cons (x, Nil)) -> compileReturnConstant x
        | Cons (Symbol name, _) -> (primitives ()).[name] form
        | _ -> invalidArg "form" "Unhandled case"

and compileMinusOrDiv (neutral: int) (op: int -> int -> int) (assocOp: int -> int -> int) (form: Value) =
    match form with
        | Cons (_, Nil) -> neutral |> Integer |> compileReturnConstant
        | Cons (_, Cons (v, Nil)) ->
            let vCompiled = compile v
            let compiled env =
                match vCompiled env with
                    | Integer x -> op neutral x |> Integer
                    | _ -> invalidArg "v" "Only integers"
            compiled
        | Cons (_, Cons (v, (Cons (_, _) as tail))) ->
            let assocOpValue x y =
                match (x, y) with
                    | (Integer vi, Integer yi) -> assocOp vi yi |> Integer
                    | (Integer _, o) -> invalidArg $"{o}" "Only integers"
                    | (o, Integer _) -> invalidArg $"{o}" "Only integers"
                    | _ -> invalidArg $"{x}, {y}" "Only integers"
            let v1 = compile v
            let v2 = compileSymmetricBinaryOperator (Integer neutral) assocOpValue (Cons (Symbol "ignored", tail))
            let compiled env =
                match (v1 env, v2 env) with
                    | (Integer val1, Integer val2) -> op val1 val2 |> Integer
                    | (Integer _, x) -> invalidArg $"{x}" "Only integers"
                    | (y, Integer _) -> invalidArg $"{y}" "Only integers"
                    | _ -> invalidArg "all" "Only integers"
            compiled
        | _ -> invalidArg $"{form}" "not a valid form for compileMinusOrDiv"

and compileSymmetricBinaryOperator acc f form =
    match form with
        | Cons (_, Nil) -> compileReturnConstant acc
        | Cons (_, (Cons (_, _) as operandForms)) ->
            let operands = mapProperList compile operandForms
            let compiled env =
                let values = List.map (fun v -> v env) operands
                List.fold f acc values
            compiled
        | _ -> invalidArg "form" "Syntax error in form"
