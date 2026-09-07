# engineering/evidence/

Captured verification output — the proof behind constitution C1 ("verification is evidence, not
assertion"). One subdirectory per feature.

```
engineering/evidence/
  F00/
    task-1.txt      # captured output of F00-T1's verification command (shows pass)
    task-2.txt
    <name>.png      # screenshot/recording for any visual task
  F01/
    ...
```

Rules (conventions §3):

- A task is done only when its named verification command has run, its output is saved here, and
  it passes. Visual work additionally needs a screenshot/recording.
- Evidence is committed **with** the task's commit (`FXX-Tn: description`).
- `engineering/evidence/` is tracked in git; it is the auditable record of what actually passed.
