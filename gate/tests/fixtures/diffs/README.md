# Adversarial diff library (conventions §2; F00 AC3–AC8)

Each file is `git diff --name-status` output against the `propositional` fixture graph, with the
claimed node `tutorial-and-swap`. `test_paths.py` asserts which step-2 rejection each produces.
Content-level cases (statement hash, proof-is-statement) are built in tests from the fixture.
