#!/usr/bin/env -S dotnet fsi
#r "System.Core.dll"
#r "System.Xml.Linq.dll"

open System.Xml.Linq

let xn s = XName.Get(s)

let fileName = if fsi.CommandLineArgs.Length < 2 then "packages.config" else fsi.CommandLineArgs[1]
    
let xmlDocument = XDocument.Load(fileName)

let packages = xmlDocument.Element(xn "packages").Elements(xn "package")

for p in packages do
    for attributeName in ["id"; "version"; "targetFramework"] do
        printfn "%s='%s'" attributeName (p.Attribute(xn attributeName).Value)
    printfn "---"
