module App

open Elmish
open Elmish.React
open Feliz

type Plate = | InsideMainStarter | InsideExtraStarter | InsideBolo | InsideExtraDish | BoloKids | ExtraDishKids | OutsideMainStarter | OutsideExtraStarter | OutsideBolo | OutsideExtraDish | OutsideDessert

let AllPlates = [InsideMainStarter; InsideExtraStarter; InsideBolo; InsideExtraDish; BoloKids; ExtraDishKids; OutsideMainStarter; OutsideExtraStarter; OutsideBolo; OutsideExtraDish; OutsideDessert]

type Tickets<'t> =
    {
        // Ordered inside a menu
        insideMainStarter : 't
        insideExtraStarter : 't
        insideBolo : 't
        insideExtraDish : 't
        // Ordered indepently of a menu
        outsideMainStarter : 't
        outsideExtraStarter : 't
        outsideBolo : 't
        outsideExtraDish : 't
        outsideDessert : 't
        // Kids menus
        boloKids : 't
        extraDishKids : 't
    }
    with member this.Get = function
                | InsideMainStarter -> this.insideMainStarter
                | InsideExtraStarter -> this.insideExtraStarter
                | InsideBolo -> this.insideBolo
                | InsideExtraDish -> this.insideExtraDish
                | BoloKids -> this.boloKids
                | ExtraDishKids -> this.extraDishKids
                | OutsideMainStarter -> this.outsideMainStarter
                | OutsideExtraStarter -> this.outsideExtraStarter
                | OutsideBolo -> this.outsideBolo
                | OutsideExtraDish -> this.outsideExtraDish
                | OutsideDessert -> this.outsideDessert

let PrixEntreeCents = 750
let PrixBoloCents = 1500
let PrixExtraDishCents = PrixBoloCents
let PrixDessertCents = 750
let PrixMenuBolo = PrixEntreeCents + PrixBoloCents + PrixDessertCents - 300
let PrixMenuExtraDish = PrixEntreeCents + PrixExtraDishCents + PrixDessertCents - 300
let PrixMenuKids = 1600

let MainStarterName = "Tomate Mozzarella"
let ExtraStarterName = "Croquettes au fromage"
let BoloName = "Spaghetti bolognaise"
let ExtraDishName = "Spaghetti végétarien"
let DessertName = "Assiette de 3 Mignardises"
let KidsSuffix = " (enfants)"
let TicketsNames = {
    insideMainStarter = MainStarterName
    insideExtraStarter = ExtraStarterName
    insideBolo = BoloName
    insideExtraDish = ExtraDishName
    outsideMainStarter = MainStarterName
    outsideExtraStarter = ExtraStarterName
    outsideBolo = BoloName
    outsideExtraDish = ExtraDishName
    outsideDessert = DessertName
    boloKids = BoloName + KidsSuffix
    extraDishKids = ExtraDishName + KidsSuffix
}

let MainStarterNamePlural = "Tomates Mozzarella"
let ExtraStarterNamePlural = "Croquettes au fromage"
let BoloNamePlural = "Spaghettis bolognaise"
let ExtraDishNamePlural = "Spaghettis végétarien"
let DessertNamePlural = "Assiettes de 3 Mignardises"
let TicketsNamesPlural = {
    insideMainStarter = MainStarterNamePlural
    insideExtraStarter = ExtraStarterNamePlural
    insideBolo = BoloNamePlural
    insideExtraDish = ExtraDishNamePlural
    outsideMainStarter = MainStarterNamePlural
    outsideExtraStarter = ExtraStarterNamePlural
    outsideBolo = BoloNamePlural
    outsideExtraDish = ExtraDishNamePlural
    outsideDessert = DessertNamePlural
    boloKids = BoloNamePlural + KidsSuffix
    extraDishKids = ExtraDishNamePlural + KidsSuffix
}

type State = {
    name : string
    email : string
    extraComment : string
    places : int
    menus : int
    kidsMenus : int
    tickets : Tickets<int>
    nameError : string option
    emailError : string option
    placesErrors : string list
    menusErrors : string list
    kidsMenusErrors : string list
    ticketsErrors : Tickets<string list>
}

type Msg =
    | SetNumberOfTickets of Plate * int
    | SetName of string
    | SetEmail of string
    | SetExtraComment of string
    | SetPlaces of int
    | SetMenus of int
    | SetKidsMenus of int

let updateTickets (tickets : Tickets<'a>) (plate: Plate) (newValue: 'a): Tickets<'a> =
    match plate with
    | InsideMainStarter -> { tickets with insideMainStarter = newValue }
    | InsideExtraStarter -> { tickets with insideExtraStarter = newValue }
    | InsideBolo -> { tickets with insideBolo = newValue }
    | InsideExtraDish -> { tickets with insideExtraDish = newValue }
    | OutsideMainStarter -> { tickets with outsideMainStarter = newValue }
    | OutsideExtraStarter -> { tickets with outsideExtraStarter = newValue }
    | OutsideBolo -> { tickets with outsideBolo = newValue }
    | OutsideExtraDish -> { tickets with outsideExtraDish = newValue }
    | OutsideDessert -> { tickets with outsideDessert = newValue }
    | BoloKids -> { tickets with boloKids = newValue }
    | ExtraDishKids -> { tickets with extraDishKids = newValue }

let updateNoValidate (msg: Msg) (state: State): State =
    match msg with
    | SetNumberOfTickets (plate, newCount) -> { state with tickets = updateTickets state.tickets plate newCount }
    | SetName newName -> { state with name = newName }
    | SetEmail newEmail -> { state with email = newEmail }
    | SetExtraComment newComment -> { state with extraComment = newComment }
    | SetPlaces newPlaces -> { state with places = newPlaces }
    | SetMenus newMenus -> { state with menus = newMenus }
    | SetKidsMenus newMenus -> { state with kidsMenus = newMenus }

let validatePositive' (count: int) (namePlural: string) (tail: string list): string list =
    if count < 0
    then (sprintf "Le nombre de %s doit être positif." namePlural :: tail)
    else tail

let validatePositive (tickets: Tickets<int>) (plate: Plate) (tail: string list): string list =
    validatePositive' (tickets.Get plate) (TicketsNamesPlural.Get plate) tail

let validateStrictPositive' (count: int) (namePlural: string) (tail: string list): string list =
    if count < 1
    then (sprintf "Le nombre de %s doit être supérieur à 0." namePlural :: tail)
    else tail

let validateStrictPositive (tickets: Tickets<int>) (plate: Plate) (tail: string list): string list =
    validateStrictPositive' (tickets.Get plate) (TicketsNamesPlural.Get plate) tail

let validateInclusiveBelow' (count: int) (namePlural: string) (max: int) (tail: string list): string list =
    if count > max
    then (sprintf "Le nombre de %s doit être inférieur ou égal à %d." namePlural max :: tail)
    else tail

let validateInclusiveBelow (tickets: Tickets<int>) (plate: Plate) (max: int) (tail: string list): string list =
    validateInclusiveBelow' (tickets.Get plate) (TicketsNamesPlural.Get plate) max tail

let naivePlural (count: int) (singular: string): string =
    match count with
    | 1 -> sprintf "1 %s" singular
    | _ -> sprintf "%d %ss" count singular

let altList (f: 'a -> 'b list) (xs: 'a) (ys: 'a): 'b list =
    match f xs with
    | [] -> f ys
    | result -> result

let FormMaxInt = 50

let validatePlatePair
        (tickets: Tickets<int>)
        (plate1: Plate)
        (plate2: Plate)
        (target: int option) =
    let plate1Count = tickets.Get plate1
    let plate1PluralName = TicketsNamesPlural.Get plate1
    let plate2Count = tickets.Get plate2
    let plate2PluralName = TicketsNamesPlural.Get plate2
    let rangeErrors =
        (validateInclusiveBelow tickets
                                plate1
                                FormMaxInt
                                (validatePositive tickets plate1 []),
         validateInclusiveBelow tickets plate2 FormMaxInt
                                (validatePositive tickets plate2 []))
    let menuErrors =
        match target with
        | None -> ([], [])
        | Some targetValue ->
            match targetValue - plate1Count - plate2Count with
            | pos when pos > 0 ->
              let msg = sprintf "Pour %s, vous devez commander plus de %s ou de %s."
                                (naivePlural targetValue "menu")
                                plate1PluralName
                                plate2PluralName
              ([msg], [msg])
            | neg when neg < 0 ->
                let msg = sprintf "Pour cette commande, vous devez commander %s en plus."
                                  (naivePlural (-neg) "menu")
                ((if plate1Count > 0 then [msg] else []),
                 (if plate2Count > 0 then [msg] else []))
            | _ -> ([], [])
    ((altList fst rangeErrors menuErrors),
     (altList snd rangeErrors menuErrors))

let validateTickets (t: Tickets<int>) (target: int option) (kidsTarget: int option): Tickets<string list> =
    let (insideMainStarter, insideExtraStarter) = validatePlatePair t InsideMainStarter InsideExtraStarter target
    let (outsideMainStarter, outsideExtraStarter) = validatePlatePair t OutsideMainStarter OutsideExtraStarter None
    let (insideBolo, insideExtraDish) = validatePlatePair t InsideBolo InsideExtraDish target
    let (outsideBolo, outsideExtraDish) = validatePlatePair t OutsideBolo OutsideExtraDish None
    let (boloKids, extraDishKids) = validatePlatePair t BoloKids ExtraDishKids kidsTarget
    let outsideDessert = validateInclusiveBelow t
                                                OutsideDessert
                                                FormMaxInt
                                                (validatePositive t OutsideDessert [])
    { insideMainStarter = insideMainStarter
      insideExtraStarter = insideExtraStarter
      insideBolo = insideBolo
      insideExtraDish = insideExtraDish
      outsideMainStarter = outsideMainStarter
      outsideExtraStarter = outsideExtraStarter
      outsideBolo = outsideBolo
      outsideExtraDish = outsideExtraDish
      outsideDessert = outsideDessert
      boloKids = boloKids
      extraDishKids = extraDishKids }

let csrfToken: string option =
    match Fable.Core.JS.eval "try { CSRF_TOKEN } catch { '' }" with
    | "" -> None
    | x -> Some x

let validateState (state: State): State =
    // let getErrorsAndTarget (count: int) (text: string): (int option, string list) =
    let getErrorsAndTarget count text =
        let errors = validateInclusiveBelow' count
                                             text
                                             FormMaxInt
                                             (validatePositive' count text [])
        let target = match errors with
                     | [] -> Some count
                     | _ -> None
        (target, errors)
    let (target, menusErrors) = getErrorsAndTarget (state.menus) "menus"
    let (kidsTarget, kidsMenusErrors) = getErrorsAndTarget (state.kidsMenus) "menus enfants"
    { state with
          nameError = if state.name.Trim() = "" then Some "Ce champ est obligatoire." else None
          emailError = match (csrfToken, state.email.Trim()) with
                       | (Some _, _) -> None
                       | (None, "") -> Some "Ce champ est obligatoire."
                       | (None, x) when (let at = x.IndexOf('@') in at > -1 && x.IndexOf('.', at) - at > 1)
                           -> None
                       | _ -> Some "Veuillez saisir une adresse email valide."
          placesErrors = validateInclusiveBelow' state.places
                                                 "places"
                                                 FormMaxInt
                                                 (validateStrictPositive' state.places "places" [])
          ticketsErrors = validateTickets state.tickets target kidsTarget
          menusErrors = menusErrors
          kidsMenusErrors = kidsMenusErrors
    }

let totalPriceInCents (state: State): int option =
    match state with
    | { ticketsErrors = { insideMainStarter = []; insideExtraStarter = []; insideBolo = []; insideExtraDish = []; boloKids = []; extraDishKids = []; outsideMainStarter = []; outsideExtraStarter = []; outsideBolo = []; outsideExtraDish = []; outsideDessert = []}
        menusErrors = []
        kidsMenusErrors = []
        tickets = tickets } ->
            tickets.insideBolo * PrixMenuBolo +
            tickets.insideExtraDish * PrixMenuExtraDish +
            (tickets.outsideMainStarter + tickets.outsideExtraStarter) * PrixEntreeCents +
            tickets.outsideBolo * PrixBoloCents +
            tickets.outsideExtraDish * PrixExtraDishCents +
            tickets.outsideDessert * PrixDessertCents +
            (tickets.boloKids + tickets.extraDishKids) * PrixMenuKids
            |> Some
    | _ -> None

let update (msg: Msg) (state: State): State =
    let newState = updateNoValidate msg state
    validateState newState

let ErrorRed = "red"

let ErrorBorderStyle =
    [style.borderColor ErrorRed; style.borderStyle.solid; style.borderWidth 1]

let errorDiv (len: Styles.ICssUnit option) (e: string) =
    let width = match len with
                | Some w -> [style.width w]
                | None -> []
    Html.div [
        [style.color ErrorRed
         style.fontStyle.oblique
         length.percent 85 |> style.fontSize] |> List.append width |> prop.style
        prop.text e]

let inputNumberRaw wrapperElt (id: string) (label: string) labelStyle (value: int) (errors: string list) (errorDivWidth: Styles.ICssUnit option) (onChange: int -> unit) =
    let basicInputProps extraStyles = [
                List.append extraStyles [
                    length.em 3 |> style.width
                    style.textAlign.right] |> prop.style
                prop.id id
                prop.name id
                prop.type' "number"
                prop.value value
                prop.onChange onChange]
    let basicChildren p = [
            Html.label [
                prop.style labelStyle
                prop.htmlFor id
                prop.text label]
            Html.input p]
    let children = match errors with
                   | [] -> basicChildren <| basicInputProps []
                   | es -> basicInputProps ErrorBorderStyle
                           |> basicChildren
                           |> List.append
                           <| List.map (errorDiv errorDivWidth) es
    wrapperElt [
        sprintf "div-just-for-%s" id |> prop.id
        prop.children children]

let inputNumber (state: State) (idPrefix: string) (plate: Plate) (onChange: int -> unit) =
    let id = sprintf "%s_%s" idPrefix <| plate.ToString().ToLower()
    let value = state.tickets.Get plate
    let errorsS = state.ticketsErrors.Get plate
    let label = TicketsNames.Get plate
    inputNumberRaw Html.li
                   id
                   label
                   [style.display.inlineBlock; length.em 15 |> style.width]
                   value
                   errorsS
                   (Some <| length.em 20)
                   onChange

let renderDessertDisplay (count: int) =
    Html.li [
        Html.text "Dessert"
        Html.ul [Html.li [Html.textf "%s: %d"
                                     ((if count = 1 then TicketsNames else TicketsNamesPlural).Get <| OutsideDessert)
                                     count]]]

let renderTicketList (choices: (string * Plate list) list) (state: State) (idPrefix: string) header (htmlTail: ReactElement list) (dispatch: Msg -> unit) =
    let setNumber p v = SetNumberOfTickets (p, v) |> dispatch
    let renderedTickets = Html.ul (
        (choices
          |> (List.map <| fun (title: string, plates: Plate list) ->
                  Html.li [
                      Html.text title
                      plates |> List.map (fun p -> setNumber p |> inputNumber state idPrefix p) |> Html.ul]))
        @ htmlTail)
    Html.div [
        prop.style [
            length.ex 1 |> style.marginRight
            style.verticalAlign.top
            style.display.inlineBlock]
        prop.children [header; renderedTickets]]

let menuHeader (count: int) formatString (dispatch: int -> unit) =
    Html.div [
        prop.children [
        Html.input [
            prop.style [
                length.em 3 |> style.width
                style.textAlign.right]
            prop.value count
            prop.type' "number"
            prop.min 0
            prop.max FormMaxInt
            dispatch |> prop.onChange]
        Html.textf formatString <| if count = 1 then "" else "s"]]

let renderInsideMenu (state: State) (dispatch: Msg -> unit) =
    let header = menuHeader (state.menus) "menu%s" (SetMenus >> dispatch)
    renderTicketList ["Entrées", [InsideMainStarter; InsideExtraStarter];
                      "Plats", [InsideBolo; InsideExtraDish]]
                     state
                     "inside"
                     header
                     [renderDessertDisplay <| state.menus]
                     dispatch

let renderKidsMenu (state: State) (dispatch: Msg -> unit) =
    let header = menuHeader (state.kidsMenus) "menu%s enfants" (SetKidsMenus >> dispatch)
    renderTicketList ["Plats", [BoloKids; ExtraDishKids]]
                     state
                     "kids"
                     header
                     [renderDessertDisplay <| state.kidsMenus]
                     dispatch

let renderOutsideMenu (state: State) (dispatch: Msg -> unit) =
    let onlyCountIfReasonable p =
        match state.ticketsErrors.Get p with
        | [] -> state.tickets.Get p
        | _ -> 0
    let outsideChoices = [("Entrées", [OutsideMainStarter; OutsideExtraStarter])
                          ("Plats", [OutsideBolo; OutsideExtraDish])
                          ("Dessert", [OutsideDessert])]
    let header = naivePlural (List.sumBy (fun (_, plates) -> List.sumBy onlyCountIfReasonable plates)
                                         outsideChoices)
                             "ticket"
              |> Html.textf "Hors menu: %s"
    renderTicketList outsideChoices
                     state
                     "outside"
                     header
                     []
                     dispatch

let inputText (id: string) (type': string) (label: string) (placeholder: string) (value: string) (error: string option) (onChange: string -> unit) =
    let basicChildren s = [
        Html.label [
            prop.style [length.ex 0.3 |> style.marginBottom]
            prop.htmlFor id
            prop.text label]
        Html.br []
        Html.input [
            prop.style <| (length.percent 100 |> style.width) :: s
            prop.id id
            prop.name id
            prop.type' type'
            length.percent 100 |> prop.width
            prop.placeholder placeholder
            prop.value value
            prop.onTextChange onChange]]
    let children =
        match error with
        | None -> basicChildren []
        | Some e -> List.append (basicChildren ErrorBorderStyle) [
            errorDiv None e]
    Html.div [
        sprintf "div-just-for-%s" id |> prop.id
        prop.style [length.ex 1 |> style.marginBottom]
        prop.children children]

let hasErrors (state: State): bool =
    Option.isSome state.nameError ||
    Option.isSome state.emailError ||
    List.exists (fun p -> List.isEmpty (state.ticketsErrors.Get p) = false) AllPlates ||
    List.isEmpty state.menusErrors = false ||
    List.isEmpty state.kidsMenusErrors = false ||
    List.isEmpty state.placesErrors = false

let render (state: State) (dispatch: Msg -> unit) =
    let hasErrors = hasErrors state
    let (secondTextInput, maybeHiddenCsrf, maybeGDPR, maybeExtraComment) =
        match csrfToken with
        // No CSRF token?  We are working for a simple user, so must validate the input and query for GDPR consent
        | None -> (inputText "email" "email" "Email:" "Votre adress email au cas où nous devions vous contacter pour votre commande",
                   Html.text "",
                   Html.div [
                       prop.style [style.overflow.hidden]
                       prop.children [
                       Html.div [
                           prop.style [length.ex 4 |> style.width; style.verticalAlign.top; style.textAlign.left; style.float'.left]
                           prop.children [
                               Html.input [
                                   prop.id "gdpr_accepts_use"
                                   prop.name "gdpr_accepts_use"
                                   prop.type' "checkbox"
                                   prop.value true]]]
                       Html.div [
                           prop.style [style.overflow.hidden; style.verticalAlign.top]
                           prop.children [
                               Html.label [
                                   prop.htmlFor "gdpr_accepts_use"
                                   prop.text "J’autorise la Société Royale d’Harmonie de Braine-l’Alleud à utiliser mon adresse email pour m’avertir de ses futures activités."]]]]],
                   Some <| inputText "extraComment" "extraComment" "Commentaire:" "Toute autre information par rapport à votre commande")
        // CSRF token?  We are working for a logged in admin, so we don't validate email but store a comment instead
        | Some x -> (inputText "comment" "text" "Commentaire:" "Commentaire optionnel, p.ex. le numéro de téléphone",
                     Html.input [prop.name "csrf_token"; prop.type' "hidden"; prop.value x],
                     Html.text "",
                     None)
    Html.form [
        prop.method "POST"
        Fable.Core.JS.eval "try { ACTION_DEST } catch { '' }" |> prop.action
        prop.children [
        inputText "name" "text" "Nom:" "Vos places et votre commande de tickets seront à votre nom" state.name state.nameError (SetName >> dispatch)
        secondTextInput state.email state.emailError (SetEmail >> dispatch)
        match maybeExtraComment with
        | None -> Html.text ""
        | Some extraCommentInput -> extraCommentInput state.extraComment None (SetExtraComment >> dispatch)
        inputNumberRaw Html.div
                       "places"
                       "Nombre de convives:"
                       []
                       state.places
                       state.placesErrors
                       None
                       (SetPlaces >> dispatch)
        Html.div [
            renderInsideMenu state dispatch
            renderKidsMenu state dispatch
            renderOutsideMenu state dispatch]
        match totalPriceInCents state with
        | None
        | Some 0 -> Html.text ""
        | Some p -> Html.textf "Prix total de votre commande: %d.%02d €." (p / 100) (p % 100)
        maybeGDPR
        if hasErrors
        then Html.text ""
        else Html.input [prop.type' "submit"; prop.value "Confirmer la réservation"]
        maybeHiddenCsrf
        Html.input [
            prop.name "date";
            prop.type' "hidden";
            Fable.Core.JS.eval "try { CONCERT_DATE } catch { '' }" |> prop.value]]]

let init() =
    let state = {
        name = ""
        email = ""
        extraComment = ""
        places = 1
        menus = 0
        kidsMenus = 0
        tickets = { insideMainStarter = 0;
                    insideExtraStarter = 0;
                    insideBolo = 0;
                    insideExtraDish = 0;
                    outsideMainStarter = 0;
                    outsideExtraStarter = 0;
                    outsideBolo = 0;
                    outsideExtraDish = 0;
                    outsideDessert = 0;
                    boloKids = 0;
                    extraDishKids = 0 }
        nameError = None
        emailError = None
        menusErrors = []
        kidsMenusErrors = []
        placesErrors = []
        ticketsErrors = { insideMainStarter = [];
                          insideExtraStarter = [];
                          insideBolo = [];
                          insideExtraDish = [];
                          outsideMainStarter = [];
                          outsideExtraStarter = [];
                          outsideBolo = [];
                          outsideExtraDish = [];
                          outsideDessert = [];
                          boloKids = [];
                          extraDishKids = [] }
    }
    validateState state

Program.mkSimple init update render
|> Program.withReactBatched "elmish-app"
|> Program.withConsoleTrace
|> Program.run
