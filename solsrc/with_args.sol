class Main : Object {
    run [ |
        s := 'Tohle je string'.
        _ := self foo: s.
    ]

    foo: [ :x |
        _ := x print.
    ]
}
