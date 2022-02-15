// 45 degrees tilted rectangle with even integer sides, count number of points
// with integer coordinates in them.
//
// - points on edges obey equations ±x ±y = √2/2 * (width or height) -> their coordinates are irrational,
//   never count them (unless width or height is 0)
// - pick L >= W (rotation of 90 degrees)

let countPointsOnDiagonal length = 2 * int(floor(double length / 2.0 / sqrt 2.0)) + 1

let rectangleRotation len wid =
    match (max len wid, min len wid) with
        | (0, 0) -> 1 // just the origin
        | (length, 0) -> countPointsOnDiagonal length
        | (length, width) ->
            let ld = countPointsOnDiagonal length
            let wd = countPointsOnDiagonal width
            let halfInterstitials = (int(floor(double width / sqrt 2.0)) + 1) / 2
            let highestDiagInside = double length / 2.0 / sqrt 2.0 |> floor |> int
            let lengthOffset =
                if ((2 * highestDiagInside + 1 |> double) < (double length / sqrt 2.0))
                then 1
                else -1
            if length = 8 && width = 4 || length = width
            then printfn "ld=%d wd=%d hI=%d hDI=%d lO=%d" ld wd halfInterstitials highestDiagInside lengthOffset
            else ()
            ld * wd + (2 * halfInterstitials * (ld + lengthOffset))

let input = [((0, 0), 1)
             ((0, 2), 1)
             ((4, 0), 3)
             ((6, 0), 5)
             ((0, 8), 5)
             ((2, 2), 5)
             ((6, 4), 23)
             ((4, 6), 23)
             ((6, 2), 13)
             ((4, 4), 13)
             ((8, 4), 27)
             ((30, 2), 65)
             ((8, 6), 49)
             ((16, 20), 333)
             ((6, 6), 41)]
for ((dim1, dim2), exp) in input do
    let computed = rectangleRotation dim1 dim2
    if computed = exp
    then printfn "ok"
    else printfn "FAIL (%d %d)->%d expected %d" dim1 dim2 computed exp

   // .  .  .  .  x
   // .  .  .  x  .
   // .  .  x  .  .
   // .  x  .  .  .
   // x  .  .  .  .
