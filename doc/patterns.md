# Programming patterns

The code makes use of the [simpy](https://simpy.readthedocs.io/en/latest/)
discrete event simulation library. This means that functions representing
processes are implemented as generators, so that the library can simulate
timeouts and asynchronous communication (typically faster than real time).

We use the convention of putting "(process)" in the doc comment of these
functions. They are also annotated with a `ProcessEffect` return type.
They either must use the `yield` construct, *or* return the result of
calling another "(process)" function (not both).

Objects that implement processes typically hold the `simpy.Environment` in
an instance variable `self.env`.

To wait for another process `f()` before continuing, use `yield from f()`.
(If it is the last thing to do in a function with no other `yield`
statements, `return f()` can be used as an optimization.)

A "(process)" function that does nothing should `return skip()`, using
`simtfl.util.skip`.


# Type annotations

The codebase is written to use static type annotations and to pass the
[pyanalyze](https://pyanalyze.readthedocs.io/en/latest/faq.html) static
analyzer.

Each source file should have `from __future__ import annotations` at
the top. This (usually) allows types defined in the same file to be
referenced before their definition, without needing the workaround of
writing such types as string literals. The preferred style is for this
line to be immediately followed by other imports that are needed for
type annotations.

The default annotation for argument and return types is `Any`. This works
well for interoperating with libraries that don't use static typing, but
please don't rely on it for code in this project. It is better to add
explicit `Any` annotations in the few cases where that is needed. This
means that functions and methods that do not return a value should be
annotated with `-> None`.

`pyanalyze` has some limitations and is not claimed to be fully sound,
but it does a pretty good job in practice; the result feels pretty much
like a statically typed variant of Python. Importing the code it checks
allows it to be more compatible with some Python idioms. The following
workarounds for its limitations may be needed:

* It is sometimes unable to see that a `None` value cannot occur in a
  particular context. In that case, adding an assertion that the value
  `is not None` may help.

* In plain Python it is common to have classes that share an interface
  and are used polymorphically, but have no superclass in common. It
  might be necessary to create an abstract base class to define the
  interface.

* There is no easy way to precisely check uses of `*args` or `**kwargs`.

* If two files have mutually dependent types, they may end up circularly
  importing each other, which Python does not support. This is more
  likely for types than for implementation code. There are several
  possible workarounds:

  * merge the files;
  * move part of one file that is causing the circularity into the
    other;
  * create an abstract base class for the type that is being used
    circularly (with methods that raise `NotImplementedError`), and
    use that as the type instead of the concrete subclass.

* Adding type annotations might require exposing internal classes that
  would otherwise be intentionally hidden. Since this hiding is normally
  only possible by convention (e.g. using underscore-prefixed names)
  in any case, that does not really cause any problem. Please just
  refrain from directly using the constructors of such classes.

As is often the case for static typing in other languages, it typically
works best to use more general types for arguments and more specific
types for results.


# Flake8

We also use [flake8](https://flake8.pycqa.org/en/latest/) to encourage
a consistent coding style. However, if you disagree with a particular
error or warning produced by `flake8` and have a good justification for
why it should not be enforced, please just add it to the `ignore` list
in `.flake8`, and document the justification there.
