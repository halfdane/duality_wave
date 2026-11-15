# Agent guidance for duality_wave

Read `CONTRIBUTING.md` for the set-up, the tasks and the code map.
The rules below replace the general rule "add tests for every behavior you add".

## Tests

The default is no new test.
Add a test only in one of two cases:
- It catches a defect that would waste a print, for example a collision, a thin wall, an invalid solid or a part that does not fit.
- It guards a mechanism with real branches, for example a geometry helper.

Do not test colours, viewer output, debug output, constants, wording or file names.
A new test is short, has one idea and states the rule in its name.
A new test builds its input from small shapes in the test file.
A new test does not use the real layout, unless the rule is about the finished case.
Use the fixtures `full`, `compact` and `quiet` only for a rule about the finished case.
Never add a fourth case build.

Take every expected value from `dims`, the switch, the specs or the layout.
Never type a number that you read from the current design.
This includes numbers in strings and in regular expressions.
Compare a label or a file with the value that the code computed, not with a pattern of digits.

When a design change breaks a test, the test is wrong.
Take the value from its source.
Do not loosen the assertion with a regex or a wider tolerance.

A unit test uses at most 1 s of CPU time.
Test a smaller shape or one builder alone.
`tests/test_hygiene.py` and `tests/conftest.py` enforce this and the number rules.

Never do these without asking the user:
- Add the `slow` marker or a line to `SLOW_BASELINE` or `LITERAL_BASELINE`.
- Add `# literal-ok:` to a line.
- Raise the CPU budget.

The `slow` marker is temporary.
It stays only on the tests in `SLOW_BASELINE` until they are fixed.

## Requirements

Do not add or change a requirement in `docs/SPEC.md` without asking.
Every requirement needs a test, so a new requirement has a steep cost.
A requirement states a physical or printable outcome.
Tooling, viewer, debug and performance behaviour is not a requirement.

## Report

List every new test with one line on the defect that it catches.
