# LaTeX Beamer presentation

The current 13-slide presentation is available as:

- [Editable LaTeX source](LLM_INVESTMENT_STUDY_20261117_beamer.tex).
- [Compiled Beamer PDF](LLM_INVESTMENT_STUDY_20261117_beamer.pdf).
- [Original slide text and speaking notes](LLM_INVESTMENT_STUDY_20261117.md).

The source is self-contained. Tables and text are native LaTeX, not screenshots.
Speaker notes remain in the source through `\note{...}` and are hidden in the
presentation PDF. The source preserves the completed EFS result, blocked
screening primary, remaining input gaps and provisional-paper status.

## Compile

Tested with TeX Live 2024 and pdfTeX 1.40.26. Standard Beamer, Latin Modern,
`array`, `ragged2e` and table-enabled `xcolor` are used. No custom fonts or
external image files are required.

From this directory, with `pdflatex` available:

```bash
beamer_build_dir=$(mktemp -d)
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory "$beamer_build_dir" LLM_INVESTMENT_STUDY_20261117_beamer.tex
pdflatex -interaction=nonstopmode -halt-on-error \
  -output-directory "$beamer_build_dir" LLM_INVESTMENT_STUDY_20261117_beamer.tex
cp "$beamer_build_dir/LLM_INVESTMENT_STUDY_20261117_beamer.pdf" .
```

On Bouchet, first load `texlive/20240312-GCC-13.3.0`. Build logs and auxiliary
files should remain in the temporary build directory, not the repository.

The earlier [rendered-slide PDF](LLM_INVESTMENT_STUDY_20261117.pdf) and the
[editable Pages deck](https://chatgpt.com/space/page_8240054152248191a27a0ae77e9bb674)
remain available. No scientific source, model, replay or account was rerun for
this format conversion.
