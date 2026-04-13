class Main : Object {
    run [ |
        i := MyClass new.
        _ := i foo.
    ]
}

class MyClass : Object {
    foo [ | _ := 'Hello from MyClass::foo' print. ]
}
