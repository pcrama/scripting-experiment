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

let digitValue = System.Globalization.CharUnicodeInfo.GetDigitValue

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

type Error = string * Input

type TokenizeResult =
    | InputExhausted
    | Token of nextInput : Input * token : Token
    | Error of Error

let tokenizeNumber c z =
    let rec goDigits w acc sign digitCount =
        let computeReturn y = Token (y, Literal(Integer(acc * sign)))
        match peekOption w with
            | None when digitCount = 0 -> Error ("Expected a number but no digits found", w)
            | None -> computeReturn w
            | Some c when isDigit c -> goDigits (advanceInput w) (10 * acc + digitValue c) sign (digitCount + 1)
            | Some c when isTokenSeparator c -> computeReturn w
            | Some c -> Error ($"The character '{c}' is not a digit while trying to tokenize a number.",
                               w)
    match c with
        | '-' -> goDigits z 0 -1 0
        | '+' -> goDigits z 0 +1 0
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
            | None -> Error ("Unterminated literal string", z)
            | Some '\\' -> advanceInput z |> goEscapedGetX (updatedAcc z)
            | Some '"' -> Token (advanceInput z, Literal(String(updatedAcc z |> reverseAndJoin)))
            | Some _ -> advanceInput z |> go acc start
    and firstGoCall acc z = go acc z.index z
    and goEscapedGetLowNibble highNibble acc z =
        let hexDigitValue c =
            if isDigit c
            then digitValue c
            else (System.Char.ToLower c |> int) - (int 'a') + 10
        match peekOption z with
            | None -> Error ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some c when (isDigit c
                           || inInclusiveRange 'A' c 'F'
                           || inInclusiveRange 'a' c 'f') -> advanceInput z |>
                                                             firstGoCall(((16 * hexDigitValue highNibble
                                                                           + hexDigitValue c)
                                                                          |> char
                                                                          |> string)
                                                                         ::acc)
            | Some c -> Error ($"Expected hexadecimal digit after '\\x' in literal string, not '{c}", z)
    and goEscapedGetHighNibble acc z =
        match peekOption z with
            | None -> Error ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some c when (isDigit c
                           || inInclusiveRange 'A' c 'F'
                           || inInclusiveRange 'a' c 'f') -> advanceInput z |> goEscapedGetLowNibble c acc
            | Some c -> Error ($"Expected hexadecimal digit after '\\x' in literal string, not '{c}", z)
    and goEscapedGetX acc z =
        match peekOption z with
            | None -> Error ("Unterminated hexadecimal escaped byte in literal string", z)
            | Some 'x' -> advanceInput z |> goEscapedGetHighNibble acc
            | Some c -> Error ($"Expected 'x' after '\\' in literal string, not '{c}", z)
    firstGoCall [] z

let tokenizeSymbol z =
    let start = z.index
    let rec go w =
        let computeReturn() = Token (w, Literal(Symbol(z.text.Substring(start, w.index - start))))
        match peekOption w with
            | None when w.index = start -> Error ("Expected a symbol, got end of input", w)
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
                    | c -> Error ($"Unexpected character '{c}'", z)

type ParseResult =
    | Parsed of nextInput: Input * value : Value
    | Error of Error

// LeftParen is already consumed
let rec parseList (s : Input) result =
    let loop i v = parseList i (dappend result v)
    match tokenize s with
        | InputExhausted -> Error ("Unterminated list", s)
        | TokenizeResult.Error e -> Error e
        | Token (nextInput, LeftParen) ->
            match parseList nextInput dnil with
                | Parsed (further, v) -> loop further v
                | Error e -> Error e
        | Token (nextInput, RightParen) ->
            Parsed (nextInput, dlistToConses result)
        | Token (nextInput, Literal v) ->
            loop nextInput v

let parse input =
    match tokenize input with
        | TokenizeResult.InputExhausted -> Error ("End of input while parsing", input)
        | TokenizeResult.Error e -> Error e
        | TokenizeResult.Token (nextInput, Literal v) ->
            Parsed (nextInput, v)
        | TokenizeResult.Token (nextInput, LeftParen) ->
            parseList nextInput dnil
        | TokenizeResult.Token (_, tok) ->
            Error ($"Unexpected token {tok}", input)

let parse1 input =
    match parse input with
        | Parsed (nextInput, v) ->
            match tokenize nextInput with
                | TokenizeResult.InputExhausted -> Parsed (nextInput, v)
                | TokenizeResult.Error e -> Error e
                | _ -> Error ("Trailing garbage after expression", nextInput)
        | err -> err
