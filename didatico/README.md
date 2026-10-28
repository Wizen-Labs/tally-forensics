# didatico: aprenda apuração ao vivo com Python

The teaching edition of the independent Colab system (`colab/`), in Portuguese, for beginner programmers.

- `aprenda_apuracao_ao_vivo.ipynb` is the notebook. Every piece of code is inline, in small cells, each preceded by
  an explanation. It covers the four challenges:
  - polite fast downloading (rate limit, HTTP 429, conditional requests, priority);
  - hashes and integrity;
  - municipal vs. section-level data;
  - the swing model and its maths.

  It also has a section on the bugs found in testing (FINDINGS P8–P10) and exercises.
- `MANUAL_COLAB.md` (Portuguese) is a short guide for helpers: Google account, Drive shortcut, Colab, and election day.
- `gerar_notebook.py` generates the notebook. Edit the generator, not the `.ipynb`, then run
  `python didatico/gerar_notebook.py`.

**Behaviour:** the same as `colab/tally_colab.py`. It was verified locally on 2026-10-14 against round 1 (`6257`), with
one 100-municipality cycle and one loop iteration: the projection was 51.0115%, equal to the official result.

This is phase-2 material: it is excluded from the public export until after the election.
