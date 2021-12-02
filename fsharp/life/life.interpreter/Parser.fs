module life.interpreter.Parser

type Value =
    | Symbol of name : string
    | Integer of integer : int
    | Nil
    | Cons of car : Value * cdr : Value
    | String of str : string

type Input =
    { text: string
      index : int }

// Inspired by https://hackage.haskell.org/package/dlist-0.5/docs/Data-DList.html
let dnil = id

let dcons c (tail : Value -> Value) =
    let f x = Cons (c, (tail x))
    f

let dappend (dlist : Value -> Value) (c : Value) =
    let f x = Cons (c, x) |> dlist
    f

let dlistToConses d = d Nil

let isDigit c = System.Char.IsDigit c

let digitValue = System.Globalization.CharUnicodeInfo.GetDigitValue >> uint32

let isTokenSeparator c = c = '(' || c = ')' || c = ';' || System.Char.IsWhiteSpace c

let advanceInput x = { x with index = x.index + 1 }

let inputExhausted y = y.index >= y.text.Length

let peek y = y.text.[y.index]

let peekOption y =
    if inputExhausted y
    then None
    else Some (peek y)

let peekIsWhiteSpace y = System.Char.IsWhiteSpace(y.text, y.index)

let peekIsDigit y = System.Char.IsDigit(y.text, y.index)

let rec skipWhitespace y =
    if inputExhausted y
    then None
    elif peekIsWhiteSpace y
    then advanceInput y |> skipWhitespace
    else Some y

let rec skipToEol y =
    if inputExhausted y
    then y
    elif peek y <> '\n' // skipToEol will skip over \r\n (CRLF) and \n (LF)
    then advanceInput y |> skipToEol
    else y

type Token =
    | LeftParen
    | RightParen
    | Literal of Value
    // | LiteralString of literal : string
    // | Symbol of name : string
    // | Integer of integer : int

let inInclusiveRange lower x upper = lower <= x && x <= upper

type ErrorT = string * Input

type TokenizeResult =
    | InputExhausted
    | Token of nextInput : Input * token : Token
    | TError of ErrorT

let tokenizeNumber c z =
    let rec goDigits w acc sign digitCount =
        let computeReturn y = Token (y, Literal(Integer(int acc * sign)))
        let maxAcc = if sign = 1 then 0x80000000u - 1u else 0x80000000u
        match peekOption w with
            | None when digitCount = 0 -> TError ("Expected a number but no digits found", w)
            | None -> computeReturn w
            | Some c when isDigit c ->
                let digit = digitValue c
                // 10u * acc + digitValue c > maxAcc <=> acc > (maxAcc - digitValue c) / 10u
                if acc > (maxAcc - digit) / 10u
                then TError ("Integer overflow", w)
                else goDigits (advanceInput w) (10u * acc + digit) sign (digitCount + 1)
            | Some c when isTokenSeparator c -> computeReturn w
            | Some c -> TError ($"The character '{c}' is not a digit while trying to tokenize a number.",
                                w)
    match c with
        | '-' -> goDigits z 0u -1 0
        | '+' -> goDigits z 0u +1 0
        | _ -> goDigits z (digitValue c) +1 1

let reverseAndJoin (x : string list) =
    let rec loop (acc : string list) = function
        | []         -> System.String.Join("", acc)
        | hd :: tail -> loop (hd::acc) tail
    loop [] x

let tokenizeLiteralString z =
    let rec go (acc : List<string>) start z =
        let updatedAcc z =
            if z.index > start
            then z.text.Substring(start, z.index - start) :: acc
            else acc
        match peekOption z with
            | None -> TError ("Unterminated literal string", z)
            | Some '\\' -> advanceInput z |> goEscapedGetX (updatedAcc z)
            | Some '"' -> Token (advanceInput z, Literal(String(updatedAcc z |> reverseAndJoin)))
            | Some _ -> advanceInput z |> go acc start
    and firstGoCall acc z = go acc z.index z
    and goEscapedGetLowNibble highNibble acc z =
        let hexDigitValue c =
            if isDigit c
            then digitValue c
            else (System.Char.ToLower c |> uint32) - uint32 'a' + 10u
        match peekOption z with
            | None -> TError ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some c when (isDigit c
                           || inInclusiveRange 'A' c 'F'
                           || inInclusiveRange 'a' c 'f') -> advanceInput z |>
                                                             firstGoCall(((16u * hexDigitValue highNibble
                                                                           + hexDigitValue c)
                                                                          |> char
                                                                          |> string)
                                                                         ::acc)
            | Some c -> TError ($"Expected hexadecimal digit after '\\x' in literal string, not '{c}", z)
    and goEscapedGetHighNibble acc z =
        match peekOption z with
            | None -> TError ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some c when (isDigit c
                           || inInclusiveRange 'A' c 'F'
                           || inInclusiveRange 'a' c 'f') -> advanceInput z |> goEscapedGetLowNibble c acc
            | Some c -> TError ($"Expected hexadecimal digit after '\\x' in literal string, not '{c}", z)
    and goEscapedGetX acc z =
        match peekOption z with
            | None -> TError ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some 'x' -> advanceInput z |> goEscapedGetHighNibble acc
            | Some c -> TError ($"Expected 'x' after '\\' in literal string, not '{c}", z)
    firstGoCall [] z

let tokenizeSymbol z =
    let start = z.index
    let rec go w =
        let computeReturn() = Token (w, Literal(Symbol(z.text.Substring(start, w.index - start))))
        match peekOption w with
            | None when w.index = start -> TError ("Expected a symbol, got end of input", w)
            | None -> computeReturn()
            | Some c when c = '_' || System.Char.IsLetterOrDigit c -> advanceInput w |> go
            | Some _ -> computeReturn()
    go z

let rec tokenize y =
    match skipWhitespace y with
        | None -> InputExhausted
        | Some z when inputExhausted z -> InputExhausted
        | Some z -> let advanceAndReturn t = Token (advanceInput z, t)
                    match peek z with
                    | ';' -> // skip comments
                        skipToEol z |> tokenize
                    | '(' -> advanceAndReturn Token.LeftParen
                    | ')' -> advanceAndReturn Token.RightParen
                    | '"' -> advanceInput z |> tokenizeLiteralString
                    | c when c = '-' || c = '+' || isDigit c -> advanceInput z |> tokenizeNumber c
                    | c when (c = '_'
                              || inInclusiveRange 'A' c 'Z'
                              || inInclusiveRange 'a' c 'z') -> tokenizeSymbol z
                    | c -> TError ($"Unexpected character '{c}'", z)

type ParseResult =
    | Parsed of nextInput: Input * value : Value
    | PError of ErrorT

// LeftParen is already consumed
let rec parseList (s : Input) result =
    let loop i v = parseList i (dappend result v)
    match tokenize s with
        | InputExhausted -> PError ("Unterminated list", s)
        | TError e -> PError e
        | Token (nextInput, LeftParen) ->
            match parseList nextInput dnil with
                | Parsed (further, v) -> loop further v
                | PError e as parseError -> parseError
        | Token (nextInput, RightParen) ->
            Parsed (nextInput, dlistToConses result)
        | Token (nextInput, Literal v) ->
            loop nextInput v

let parse input =
    match tokenize input with
        | TokenizeResult.InputExhausted -> PError ("End of input while parsing", input)
        | TError e -> PError e
        | TokenizeResult.Token (nextInput, Literal v) ->
            Parsed (nextInput, v)
        | TokenizeResult.Token (nextInput, LeftParen) ->
            parseList nextInput dnil
        | TokenizeResult.Token (_, tok) ->
            PError ($"Unexpected token {tok}", input)

let parse1 input =
    match parse input with
        | Parsed (nextInput, v) ->
            match tokenize nextInput with
                | TokenizeResult.InputExhausted -> Parsed (nextInput, v)
                | TError e -> PError e
                | _ -> PError ("Trailing garbage after expression", nextInput)
        | err -> err
