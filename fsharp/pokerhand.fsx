#r "nuget: Fuchu, 1.1.0"
open System

type Result =
| Win = 0 
| Loss = 1
| Tie = 2

type Suit = | Spades | Hearts | Diamonds | Clubs

type Value = | V2 = 2 | V3 = 3 | V4 = 4 | V5 = 5 | V6 = 6 | V7 = 7 | V8 = 8 | V9 = 9 | V10 = 10 | Jack = 11 | Queen = 12 | King = 13 | Ace = 14

type Card (s: string) =
  let parseValue c =
    match c with
      | 'A' -> Value.Ace
      | 'K' -> Value.King
      | 'Q' -> Value.Queen
      | 'J' -> Value.Jack
      | '2' -> Value.V2
      | '3' -> Value.V3
      | '4' -> Value.V4
      | '5' -> Value.V5
      | '6' -> Value.V6
      | '7' -> Value.V7
      | '8' -> Value.V8
      | '9' -> Value.V9
      | 'T' -> Value.V10
      | _ -> failwith "Invalid value"
  let parseSuit c =
    match c with
      | 'S' -> Spades
      | 'H' -> Hearts
      | 'D' -> Diamonds
      | 'C' -> Clubs
      | _ -> failwith "Invalid suit"
  let value = parseValue(s.[0])
  let suit = parseSuit(s.[1])
  member val Value = value
  member val Suit = suit
  interface System.IComparable<Card> with
      member this.CompareTo other =
          let valueComparison = compare this.Value other.Value
          if valueComparison = 0
          then compare this.Suit other.Suit
          else valueComparison
  interface IComparable with
      member this.CompareTo obj =
          match obj with
              | null             -> 1
              | :? Card as other -> (this :> IComparable<Card>).CompareTo other
              | _                -> invalidArg (nameof obj) "not a Card"
  interface IEquatable<Card> with
      member this.Equals other =
          this.Value = other.Value && this.Suit = other.Suit
  override this.Equals obj =
      match obj with
          | null -> false
          | :? Card as other ->
              this.Value = other.Value && this.Suit = other.Suit
          | _ -> false
  override this.GetHashCode () =
      this.Value.GetHashCode() * 37 + this.Suit.GetHashCode()

let getCardValue (c: Card) = c.Value

type ParsedHand =
  | Highcard of Value list // sorted from highest to lowest
  | Pair of Value * Value list // sorted from highest to lowest
  | TwoPairs of Value * Value * Value // sorted from highest to lowest
  | Three of Value * Value list // sorted from highest to lowest
  | Straight of Value // highest card of straight (contiguous sequence, Ace is 1 or max)
  | Flush of Value list // sorted from highest to lowest, same suit for every card
  | FullHouse of Value * Value // triple * pair
  | Four of Value * Value // 4 times + remaining card
  | StraightFlush of Card // highest card of straight (straight of same suit)
  | RoyalFlush of Suit // straight flush from Ace down to 10

let diffRev f xs =
    let rec go acc prev ys =
        match ys with
            | y :: tail -> go ((f prev y)::acc) y tail
            | [] -> acc
    match xs with
        | x :: (_ :: _ as tail) -> go [] x tail
        | [_] -> invalidArg (nameof xs) "invalid number of elements in input"
        | [] -> []

// Assumes cards are already sorted from highest to lowest
let isFlush (cards: Card list) =
    let headCard = List.head cards
    if List.forall (fun (c: Card) -> c.Suit = headCard.Suit) cards
    then Flush (List.map getCardValue cards) |> Some
    else None

// Assumes cards are already sorted from highest to lowest
let isStraight (cards: Card list) =
    match cards |> List.map (getCardValue >> int) |> diffRev (fun x y -> x - y) with
        | [1; 1; 1; 1] -> Straight (List.head cards).Value |> Some
        // Ace; 5; 4; 3; 2 Ace is Straight [5; 4; 3; 2; Ace]
        | [1; 1; 1; 9] -> Straight Value.V5 |> Some
        | _ -> None
    
// Assumes cards are already sorted from highest to lowest
let isStraightFlush (cards: Card list) =
    match (isStraight cards, isFlush cards) with
        | (Some (Straight _), Some (Flush _)) -> List.head cards |> StraightFlush |> Some
        | _ -> None

// Assumes cards are already sorted from highest to lowest
let isRoyalFlush (cards: Card list) =
  match isStraightFlush cards with
      | Some (StraightFlush c)
        when c.Value = Value.Ace && List.forall (fun (o: Card) -> o.Suit = c.Suit) cards
        -> RoyalFlush c.Suit |> Some
      | _ -> None

let firstSome fs defaultFunction x =
    let rec go = function
        | [] -> defaultFunction x
        | f :: tail -> match f x with
                           | Some result -> result
                           | None -> go tail
    go fs

let isGrouped (cards: Card list) =
    let grouped = List.groupBy getCardValue cards
               |> List.map (fun (v: Value, cs: Card list) -> (v, List.length cs))
               |> List.sortByDescending snd
    match grouped with
        | [(v, 4); (o, 1)] -> Four (v, o) |> Some
        | [(v, 3); (o, 2)] -> FullHouse (v, o) |> Some
        | [(v, 3); (o, 1); (p, 1)] -> Three (v, [max o p; min o p]) |> Some
        | [(v, 2); (w, 2); (o, 1)] -> TwoPairs (max v w, min w v, o) |> Some
        | (v, 2) :: _ ->
            Pair (v,
                  List.filter (fun (o: Card) -> o.Value <> v) cards
                  |> List.map getCardValue)
            |> Some
        | _ -> None
        
let parseHand (s: string) =
  let cards = s.Split ' ' |> Seq.map Card |> Seq.sortDescending |> Seq.toList
  firstSome [isRoyalFlush
             isStraightFlush
             isStraight
             isFlush
             isGrouped]
            (List.map getCardValue >> Highcard)
            cards

let compareToResult a b =
    if a > b
    then Result.Win
    elif a < b
    then Result.Loss
    else Result.Tie

type Pokerhand (hand: string) =
    let parsed = parseHand hand
    member val Parsed = parsed
    member this.compareWith (pokerhand: Pokerhand) = compareToResult this.Parsed pokerhand.Parsed
       // match (this.Parsed, pokerhand.Parsed) with
       //     | (RoyalFlush _, RoyalFlush _) -> Result.Tie
       //     | (StraightFlush me, StraightFlush other) ->
       //         compareToResult me other
       //     | ((Four (_, _) as mine), (Four (_, _) as hers)) ->
       //         compareToResult mine hers
       //     | ((FullHouse (_, _) as mine), (FullHouse (_, _) as hers)) ->
       //         compareToResult mine hers
       //     | _ -> Result.Loss

module Tests = begin
    open Fuchu

    let testParser input (expected: ParsedHand) =
        testCase ("Testing '" + input + "'") (fun _ -> Assert.Equal("", expected, parseHand input))

    let suite = testList "Tests" [
                  testList "Hand parser" [
                      testParser "AH TH 5H 8H KH" (Flush [Value.Ace; Value.King; Value.V10; Value.V8; Value.V5])
                      testParser "AH 3H 5C 2S KC" (Highcard [Value.Ace; Value.King; Value.V5; Value.V3; Value.V2])
                      testParser "AH 2S 3H 5C KC" (Highcard [Value.Ace; Value.King; Value.V5; Value.V3; Value.V2])
                      testParser "AH TH JH KH QH" (RoyalFlush Hearts)
                      testParser "AH TC JH KH QH" (Straight Value.Ace)
                      testParser "AH 2C 5H 3C 4D" (Straight Value.V5)
                      testParser "6S 2C 5H 3C 4D" (Straight Value.V6)
                      testParser "AC TC JC KC QC" (RoyalFlush Clubs)
                      testParser "KC 7D 2S 5S KH" (Pair (Value.King, [Value.V7; Value.V5; Value.V2]))
                      testParser "7D KC 2S 7S KH" (TwoPairs (Value.King, Value.V7, Value.V2))
                      testParser "7D 7C 2S 7S KH" (Three (Value.V7, [Value.King; Value.V2]))
                      testParser "7D 8H TC JD 9D" (Straight Value.Jack)
                  ]
                  testList "Bingo Number Caller" [
                    testCase "Highest straight flush wins" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("2H 3H 4H 5H 6H").compareWith(Pokerhand("KS AS TS QS JS"))))
                    testCase "Straight flush wins of 4 of a kind" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("2H 3H 4H 5H 6H").compareWith(Pokerhand("AS AD AC AH JD"))))
                    testCase "Highest 4 of a kind wins" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("AS AH 2H AD AC").compareWith(Pokerhand("JS JD JC JH 3D"))))
                    testCase "4 Of a kind wins of full house" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("2S AH 2H AS AC").compareWith(Pokerhand("JS JD JC JH AD"))))
                    testCase "Full house wins of flush" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("2S AH 2H AS AC").compareWith(Pokerhand("2H 3H 5H 6H 7H"))))
                    testCase "Highest flush wins" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("AS 3S 4S 8S 2S").compareWith(Pokerhand("2H 3H 5H 6H 7H"))))
                    testCase "Flush wins of straight" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("2H 3H 5H 6H 7H").compareWith(Pokerhand("2S 3H 4H 5S 6C"))))
                    testCase "Equal straight is tie" <| (fun _ -> Assert.Equal("", Result.Tie, Pokerhand("2S 3H 4H 5S 6C").compareWith(Pokerhand("3D 4C 5H 6H 2S"))))
                    testCase "Straight wins of three of a kind" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("2S 3H 4H 5S 6C").compareWith(Pokerhand("AH AC 5H 6H AS"))))
                    testCase "3 Of a kind wins of two pair" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("2S 2H 4H 5S 4C").compareWith(Pokerhand("AH AC 5H 6H AS"))))
                    testCase "2 Pair wins of pair" <| (fun _ -> Assert.Equal("", Result.Win, Pokerhand("2S 2H 4H 5S 4C").compareWith(Pokerhand("AH AC 5H 6H 7S"))))
                    testCase "Highest pair wins" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("6S AD 7H 4S AS").compareWith(Pokerhand("AH AC 5H 6H 7S"))))
                    testCase "Pair wins of nothing" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("2S AH 4H 5S KC").compareWith(Pokerhand("AH AC 5H 6H 7S"))))
                    testCase "Highest card wins" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("2S 3H 6H 7S 9C").compareWith(Pokerhand("7H 3C TH 6H 9S"))))
                    testCase "Highest card loses" <| (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("3S 5H 6H TS AC").compareWith(Pokerhand("4S 5H 6H TS AC"))))
                    testCase "Highest full house wins 1" (fun _ -> Assert.Equal("", Result.Loss, Pokerhand("3S 3H TH TS 3D").compareWith(Pokerhand("3D 3S 3H JH JC"))))
                    testCase "Highest full house wins 2" (fun _ -> Assert.Equal("", Result.Win, Pokerhand("4S 4H 4H TS TD").compareWith(Pokerhand("3D 3S 3H JH JC"))))
                    testCase "Equal cards is tie" <| (fun _ -> Assert.Equal("", Result.Tie, Pokerhand("2S AH 4H 5S 6C").compareWith(Pokerhand("AD 4C 5H 6H 2C"))))    
                  ]
                ]

    let doit () =
        suite |> run
end

Tests.doit()
