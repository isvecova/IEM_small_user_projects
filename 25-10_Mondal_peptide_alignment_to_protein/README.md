# Peptide coverage of a protein sequence

## Goal

Find exact occurrences of peptide sequences within a protein and summarize which amino acids are covered. Matching is case-sensitive and uses exact substrings; mismatches and gaps are not supported.

## Input

- A FASTA file containing one protein sequence; the example is [S288C_YGL173C_XRN1_protein.fsa](S288C_YGL173C_XRN1_protein.fsa).
- A text file with one peptide sequence per line; the example is [peptides.txt](peptides.txt). Use consistent capitalization and no extra spaces around sequences.

## Output

The script writes these files in the configured working directory:

- `alignment.html`: protein coverage and matching peptides, viewable in a web browser.
- `intervals.csv`: covered/uncovered intervals with 1-based, inclusive amino-acid coordinates; open in a spreadsheet.
- `summary.txt`: coverage percentage and peptides with no matches or multiple occurrences.

## How to use

1. Install [Miniforge](https://conda-forge.org/download/) and open Miniforge Prompt:

   ```bash
   conda create -n peptide-coverage python=3.11 -y
   conda activate peptide-coverage
   python -m pip install matplotlib ipython
   ```

   These packages are imported by the script; FASTA parsing and matching use Python's standard library.

2. Open [align_to_protein_script.py](align_to_protein_script.py). Change `os.chdir(...)` to the folder with your input files and set `protein_file` and `peptides_file`.
3. From this project folder, run:

   ```bash
   python align_to_protein_script.py
   ```

4. Open `alignment.html` and review `summary.txt`, especially unmatched or multiply matched peptides.

The `.ipynb` files contain exploratory and notebook-based alternatives. The standalone script is the main entry point. Existing output files with the same names are replaced on rerun.
