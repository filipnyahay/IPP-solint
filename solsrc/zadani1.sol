class Main : Object {
    run [ |
        a := self attrib: 10.
        b := [ | x := ((self attrib) asString) concatenateWith: (10 asString). ].
    ]
}
