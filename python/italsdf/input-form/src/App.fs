module App

open Elmish
open Elmish.React
open Feliz

type PlateType = | InsideMenu | OutsideMenu

type Plate = | Assiettes | Fondus | Bolo | Scampis | Tiramisu | Tranches

let AllPlates = [Assiettes; Fondus; Bolo; Scampis; Tiramisu; Tranches]

type Tickets<'t> =
    {
        assiettes : 't
        fondus : 't
        bolo : 't
        scampis : 't
        tiramisu : 't
        tranches : 't
    }
    with member this.Get = function
                | Assiettes -> this.assiettes
                | Fondus -> this.fondus
                | Bolo -> this.bolo
                | Scampis -> this.scampis
                | Tiramisu -> this.tiramisu
                | Tranches -> this.tranches

let PrixEntreeEuros = 9
let PrixBoloEuros = 12
let PrixScampisEuros = PrixBoloEuros + 5
let PrixDessertEuros = 6
let PrixMenuBolo = PrixEntreeEuros + PrixBoloEuros + PrixDessertEuros - 2
let PrixMenuScampis = PrixEntreeEuros + PrixScampisEuros + PrixDessertEuros - 2

let TicketsNames = {
    assiettes = "Assiette italienne"
    fondus = "Croquettes au fromage"
    bolo = "Spaghetti bolognaise"
    scampis = "Spaghetti aux scampis"
    tiramisu = "Tiramisu maison"
    tranches = "Tranche napolitaine"
}

type State =
    {
        name : string
        email : string
        places : int
        menus : int
        insideMenu : Tickets<int>
        outsideMenu : Tickets<int>
        nameError : string option
        emailError : string option
        placesErrors : string list
        menusErrors : string list
        insideMenuErrors : Tickets<string list>
        outsideMenuErrors : Tickets<string list>
    }

type Msg =
    | SetNumberOfTickets of PlateType * Plate * int
    | SetName of string
    | SetEmail of string
    | SetPlaces of int
    | SetMenus of int

let updateMenu (tickets : Tickets<'a>) (plate: Plate) (newValue: 'a): Tickets<'a> =
    match plate with
    | Assiettes -> { tickets with assiettes = newValue }
    | Fondus -> { tickets with fondus = newValue } 
    | Bolo -> { tickets with bolo = newValue } 
    | Scampis -> { tickets with scampis = newValue } 
    | Tiramisu -> { tickets with tiramisu = newValue } 
    | Tranches -> { tickets with tranches = newValue }

let updateNoValidate (msg: Msg) (state: State): State =
    match msg with
    | SetNumberOfTickets (plateType, plate, newCount) ->
        match plateType with
        | InsideMenu -> { state with insideMenu = updateMenu state.insideMenu plate newCount }
        | OutsideMenu -> { state with outsideMenu = updateMenu state.outsideMenu plate newCount }
    | SetName newName -> { state with name = newName }
    | SetEmail newEmail -> { state with email = newEmail }
    | SetPlaces newPlaces -> { state with places = newPlaces }
    | SetMenus newMenus -> { state with menus = newMenus }

let validatePositive (count: int) (namePlural: string) (tail: string list): string list =
    if count < 0
    then (sprintf "Le nombre de %s doit être positif." namePlural :: tail)
    else tail

let validateStrictPositive (count: int) (namePlural: string) (tail: string list): string list =
    if count < 1
    then (sprintf "Le nombre de %s doit être supérieur à 0." namePlural :: tail)
    else tail

let validateInclusiveBelow (count: int) (namePlural: string) (max: int) (tail: string list): string list =
    if count > max
    then (sprintf "Le nombre de %s doit être inférieur ou égal à %d." namePlural max :: tail)
    else tail

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
        (plate1Count: int)
        (plate1PluralName: string)
        (plate2Count: int)
        (plate2PluralName: string)
        (target: int option) =
    let rangeErrors =
        (validateInclusiveBelow plate1Count
                                plate1PluralName
                                FormMaxInt
                                (validatePositive plate1Count plate1PluralName []),
         validateInclusiveBelow plate2Count plate2PluralName FormMaxInt
                                (validatePositive plate2Count plate2PluralName []))
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

let validateTickets (t: Tickets<int>) (target: int option): Tickets<string list> =
    let (assiettes, fondus) = validatePlatePair t.assiettes "Assiettes italiennes" t.fondus "Croquettes au fromage" target
    let (bolo, scampis) = validatePlatePair t.bolo "Spaghettis bolognaise" t.scampis "Spaghettis aux scampis" target
    let (tiramisu, tranches) = validatePlatePair t.tiramisu "Tiramisus" t.tranches "Tranches napolitaines" target
    { assiettes = assiettes
      fondus = fondus
      bolo = bolo
      scampis = scampis
      tiramisu = tiramisu
      tranches = tranches }

let csrfToken: string option =
    match Fable.Core.JS.eval "try { CSRF_TOKEN } catch { '' }" with
    | "" -> None
    | x -> Some x

let validateState (state: State) =
    let menusErrors = validateInclusiveBelow state.menus
                                             "menus"
                                             FormMaxInt
                                             (validatePositive state.menus "menus" [])
    let target = match menusErrors with
                 | [] -> Some state.menus
                 | _ -> None
    { state with
          nameError = if state.name.Trim() = "" then Some "Ce champ est obligatoire." else None
          emailError = match (csrfToken, state.email.Trim()) with
                       | (Some _, _) -> None
                       | (None, "") -> Some "Ce champ est obligatoire."
                       | (None, x) when (let at = x.IndexOf('@') in at > -1 && x.IndexOf('.', at) - at > 1)
                           -> None
                       | _ -> Some "Veuillez saisir une adresse email valide."
          placesErrors = validateInclusiveBelow state.places
                                                "places"
                                                FormMaxInt
                                                (validateStrictPositive state.places "places" [])
          insideMenuErrors = validateTickets state.insideMenu target
          outsideMenuErrors = validateTickets state.outsideMenu None
          menusErrors = menusErrors
    }

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

let inputNumber (tickets: Tickets<int>) (errors: Tickets<string list>) (idPrefix: string) (plate: Plate) (onChange: int -> unit) =
    let id = sprintf "%s_%s" idPrefix <| plate.ToString().ToLower()
    let value = tickets.Get plate
    let errorsS = errors.Get plate
    let label = TicketsNames.Get plate
    inputNumberRaw Html.li
                   id
                   label
                   [style.display.inlineBlock; length.em 15 |> style.width]
                   value
                   errorsS
                   (Some <| length.em 20)
                   onChange

let renderTicket (isMenu: PlateType) (state: State) (dispatch: Msg -> unit) =
    let setNumber p v = SetNumberOfTickets (isMenu, p, v) |> dispatch
    let mkInput, header =
        match isMenu with
        | InsideMenu ->
            (inputNumber state.insideMenu state.insideMenuErrors "inside",
             Html.div [
                prop.children [
                Html.input [
                    prop.style [
                        length.em 3 |> style.width
                        style.textAlign.right]
                    prop.value state.menus
                    prop.type' "number"
                    prop.min 0
                    prop.max FormMaxInt
                    SetMenus >> dispatch |> prop.onChange]
                Html.textf " menu%s" <| if state.menus = 1 then "" else "s"]])
        | OutsideMenu ->
            let onlyCountIfReasonable p =
                match state.outsideMenuErrors.Get p with
                | [] -> state.outsideMenu.Get p
                | _ -> 0
            (inputNumber state.outsideMenu state.outsideMenuErrors "outside",
             naivePlural (List.sumBy onlyCountIfReasonable AllPlates)
                         "ticket"
             |> Html.textf "Hors menu: %s")
    let renderedTicket =
        [("Entrées", [Assiettes; Fondus])
         ("Plats", [Bolo; Scampis])
         ("Desserts", [Tiramisu; Tranches])]
        |> (List.map <| fun (title: string, plates) ->
               Html.li [
                   Html.text title
                   plates |> List.map (fun p -> setNumber p |> mkInput p) |> Html.ul])
        |> Html.ul
    Html.div [
        prop.style [
            length.ex 1 |> style.marginRight
            style.verticalAlign.top
            style.display.inlineBlock]
        prop.children [header; renderedTicket]]

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

let totalPriceInEuros (state: State): int =
    state.insideMenu.bolo * PrixMenuBolo +
    state.insideMenu.scampis * PrixMenuScampis +
    (state.outsideMenu.assiettes + state.outsideMenu.fondus) * PrixEntreeEuros +
    state.outsideMenu.bolo * PrixBoloEuros +
    state.outsideMenu.scampis * PrixScampisEuros +
    (state.outsideMenu.tiramisu + state.outsideMenu.tranches) * PrixDessertEuros

let hasErrors (state: State): bool =
    Option.isSome state.nameError ||
    Option.isSome state.emailError ||
    List.exists (fun p -> List.isEmpty (state.insideMenuErrors.Get p) = false) AllPlates ||
    List.exists (fun p -> List.isEmpty (state.outsideMenuErrors.Get p) = false) AllPlates ||
    List.isEmpty state.menusErrors = false ||
    List.isEmpty state.placesErrors = false

let render (state: State) (dispatch: Msg -> unit) =
    let hasErrors = hasErrors state
    let (secondTextInput, maybeHiddenCsrf) =
        match csrfToken with
        // No CSRF token?  We are working for a simple user, so must validate the input.
        | None -> (inputText "email" "email" "Email:" "Nous pourrions avoir besoin de votre email pour le tracing", Html.text "")
        // CSRF token?  We are working for a logged in admin, so we don't validate email but store a comment instead
        | Some x -> (inputText "comment" "text" "Commentaire:" "Commentaire optionnel, p.ex. le numéro de téléphone",
                     Html.input [prop.name "csrf_token"; prop.type' "hidden"; prop.value x])
    Html.form [
        prop.method "POST"
        Fable.Core.JS.eval "try { ACTION_DEST } catch { '' }" |> prop.action
        prop.children [
        inputText "name" "text" "Nom:" "Vos places et votre commande de tickets seront à votre nom" state.name state.nameError (SetName >> dispatch)
        secondTextInput state.email state.emailError (SetEmail >> dispatch)
        inputNumberRaw Html.div
                       "places"
                       "Nombre de convives:"
                       []
                       state.places
                       state.placesErrors
                       None
                       (SetPlaces >> dispatch)
        Html.div [
            renderTicket InsideMenu state dispatch
            renderTicket OutsideMenu state dispatch]
        match (hasErrors, totalPriceInEuros state) with
        | (true, _)
        | (false, 0) -> Html.text ""
        | (false, p) -> Html.textf "Prix total de votre commande: %d €." p
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
                        prop.text "J’autorise la Société Royale d’Harmonie de Braine-l’Alleud à utiliser mon adresse email pour m’avertir de ses futures activités."]]]]]
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
        places = 1
        menus = 0
        insideMenu = { assiettes = 0; fondus = 0; bolo = 0; scampis = 0; tiramisu = 0; tranches = 0 }
        outsideMenu = { assiettes = 0; fondus = 0; bolo = 0; scampis = 0; tiramisu = 0; tranches = 0 }
        nameError = None
        emailError = None
        menusErrors = []
        placesErrors = []
        insideMenuErrors = { assiettes = []; fondus = []; bolo = []; scampis = []; tiramisu = []; tranches = [] }
        outsideMenuErrors = { assiettes = []; fondus = []; bolo = []; scampis = []; tiramisu = []; tranches = [] }
    }
    validateState state

Program.mkSimple init update render
|> Program.withReactSynchronous "elmish-app"
|> Program.run
