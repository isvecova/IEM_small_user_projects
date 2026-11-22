import matplotlib.pyplot as plt
import os

from IPython.display import display, HTML
import html as html_mod

# CHANGE THE DIRECTORY TO WHERE THE FILES ARE LOCATED
os.chdir("D:/000_user_projects/Satya_peptide_alignment_to_protein")

# SPECIFY THE NAMES OF THE INPUT FILES
# Protein file should be in the FASTA format
protein_file = "S288C_YGL173C_XRN1_protein.fsa"
# Peptides file should be in the TXT format, one peptide sequence per line
peptides_file = "peptides.txt"



# FUNCTION DEFINITIONS
def read_fasta_single(path: str) -> str:
    # Reads a single-sequence FASTA file and returns the sequence as a string.
    seq_lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            seq_lines.append(line)
    return "".join(seq_lines).replace(" ", "").replace("\t", "")


def read_txt_many(path: str):
    # Reads a text file where each line contains a single sequence. Returns a list of lines.
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.replace("\ufeff", "")  # /ufeff occurs at the start of some files
            line = line.replace("\n", "")   # /n is a newline character
            entries.append(line)
    return entries


def compute_coverage(protein: str, peptides):
    # Computes which amino acids in the protein are covered by the given peptides. 
    # Returns a list of booleans indicating coverage and a dictionary of peptide occurrence counts.
    covered = [False] * len(protein)
    sequence_occurences = {}
    seen = set()
    for pep in peptides:
        if not pep:
            continue
        if pep in seen:
            continue
        seen.add(pep)
        n = 0
        start = 0
        while True:
            idx = protein.find(pep, start)
            if idx == -1:
                break
            for i in range(idx, idx + len(pep)):
                covered[i] = True
            n += 1
            start = idx + 1
        sequence_occurences[pep] = n
    return covered, sequence_occurences


def boolean_runs(flags):
    # Converts a list of booleans into runs of (start, end, value).
    if not flags:
        return []
    runs = []
    cur_val = flags[0]
    start = 0
    for i in range(1, len(flags)):
        if flags[i] != cur_val:
            runs.append((start, i, cur_val))
            start = i
            cur_val = flags[i]
    runs.append((start, len(flags), cur_val))
    return runs


def write_intervals_csv(path, runs):
    # Writes coverage intervals to a CSV file.
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["start_aa_1based", "end_aa_1based", "length", "covered"])
        for s, e, val in runs:
            w.writerow([s+1, e, e - s, "covered" if val else "uncovered"])


def summarize_coverage(flags):
    # Summarizes coverage statistics from a list of booleans.
    total = len(flags)
    cov = sum(1 for x in flags if x)
    uncov = total - cov
    pct = 0.0 if total == 0 else 100.0 * cov / total
    return {"total_len": total, "covered_len": cov, "uncovered_len": uncov, "percent_covered": pct}


def write_alignment_html(path, protein: str, peptides: list, flags: list):
    # Prepare peptide occurrences (start indices are 0-based)
    occurrences = []
    for pep in peptides:
        p = pep.strip().replace(" ", "").replace("\t", "")
        if not p:
            continue
        start = 0
        while True:
            idx = protein.find(p, start)
            if idx == -1:
                break
            occurrences.append((idx, p))
            start = idx + 1

   # Visual parameters
    line_width = 80

    # Build HTML with per-residue coverage coloring and peptide lines underneath
    parts = []
    parts.append("""
    <style>
      .seq {{ font-family: monospace; white-space: pre; line-height: 1.1; }}
      .covered {{ background: #c8e6c9; }}     /* light green */
      .uncovered {{ background: #ffffff; }}   /* white */
      .peptide {{ background: #fff3bf; }}     /* light yellow */
      .index {{ color: #666; font-size: 0.9em; }}
      .legend {{ font-family: sans-serif; margin-bottom: 6px; }}
    </style>
    <div class="legend">
      <span style="display:inline-block;padding:2px 6px;background:#c8e6c9;border:1px solid #b2dfbb;margin-right:8px">covered</span>
      <span style="display:inline-block;padding:2px 6px;background:#fff3bf;border:1px solid #ffeeba;">peptide</span>
      <span style="margin-left:12px;color:#666">Line width: {}</span>
    </div>
    """.format(line_width))

    parts.append('<div class="seq">')

    for line_start in range(0, len(protein), line_width):
        line_end = min(len(protein), line_start + line_width)

        # optional index line (1-based positions every 10)
        idx_line = []
        for i in range(line_start, line_end):
            if ((i + 1) % 10) == 0:
                idx_line.append(str((i + 1) % 100 // 10))  # simple tick marker
            else:
                idx_line.append(" ")
        # main protein line with per-residue spans
        prot_spans = []
        for i, aa in enumerate(protein[line_start:line_end], start=line_start):
            cls = "covered" if flags[i] else "uncovered"
            prot_spans.append(f'<span class="{cls}">{html_mod.escape(aa)}</span>')
        prot_line = "".join(prot_spans)

        # build peptide lines for any occurrence overlapping this block
        pep_lines = []
        for occ_start, pep in occurrences:
            occ_end = occ_start + len(pep)
            if occ_end <= line_start or occ_start >= line_end:
                continue  # not overlapping this block
            left = max(0, occ_start - line_start)
            clip_start = max(0, line_start - occ_start)
            clip_end = min(len(pep), line_end - occ_start)
            pep_part = pep[clip_start:clip_end]
            pad = "&nbsp;" * left
            pep_spans = "".join(f'<span class="peptide">{html_mod.escape(c)}</span>' for c in pep_part)
            pep_lines.append(pad + pep_spans)

        # position label (1-based)
        parts.append(f'<span class="index">{line_start+1:>6}</span> {prot_line}')
        for pl in pep_lines:
            parts.append(" " * 8 + pl)  # align under index + space
        parts.append("<br>")

    parts.append("</div>")

    html = "\n".join(parts)

    # save and display
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Wrote alignment HTML to: {path}")



def main(): 
    protein = read_fasta_single(protein_file)
    peptides = read_txt_many(peptides_file)
    flags, peptide_occurrences = compute_coverage(protein, peptides)
    print(peptide_occurrences)
    runs = boolean_runs(flags)

    # Outputs
    csv_path = f"intervals.csv"
    write_intervals_csv(csv_path, runs)
    write_alignment_html("alignment.html", protein, peptides, flags)

    summary = summarize_coverage(flags)
    with open(f"summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Total length: {summary['total_len']}\n")
        f.write(f"Covered length: {summary['covered_len']}\n")
        f.write(f"Uncovered length: {summary['uncovered_len']}\n")
        f.write(f"Percent covered: {summary['percent_covered']:.2f}%\n")

        # Peptides with 0 or >1 occurrences
        zeros = [p for p, c in peptide_occurrences.items() if c == 0]
        multis = {p: c for p, c in peptide_occurrences.items() if c > 1}

        f.write("\nPeptides with 0 occurrences:\n")
        if zeros:
            for p in zeros:
                f.write(f"{p}\n")
        else:
            f.write("(none)\n")
        f.write("\nPeptides with >1 occurrences:\n")
        if multis:
            for p, c in multis.items():
                f.write(f"{p}\t{c}\n")
        else:
            f.write("(none)\n")

if __name__ == "__main__":
    main()