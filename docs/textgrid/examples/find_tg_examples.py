#!/usr/bin/env python3
"""
find_tg_examples.py — locate example utterances in ParlaSpeech corpora.

Four modes
----------
doublets   Rank surface words realised with more than one primary-stress
           position across the corpus. Writes a shortlist JSONL to pick
           examples from. Requires words_align + primary_stress (HR/RS).
stress     Find every instance of a target word, optionally filtered by
           UPOS and gender, report the stress-position breakdown, then
           list/copy instances at a chosen stress position. Requires
           words_align + primary_stress (HR/RS).
fp         Find utterances with at least N filled pauses, optionally
           filtered by word and gender. Works on any language (only
           needs filled_pauses).
fp-annot   Search human-annotated TextGrid folders for a target label
           inside the fp-annotation IntervalTier, print the path and
           interval time of every hit.

Layout conventions
-------------------
--audio-root     nested "<hash>/<stem>.ext"      (flac/wav tried automatically)
--tg-root        flat folder; filename = "{audio_stem}{tg_suffix}"
                 e.g. --tg-suffix ".stress.TextGrid"
--fp-annot-dirs  searched recursively for --fp-annot-glob (default "*.TextGrid")

Arguments
---------
--mode           {doublets,stress,fp,fp-annot}   required
--jsonl          ParlaSpeech JSONL path                    [doublets, stress, fp]
--audio-root     nested audio root, required for --copy    [stress, fp]
--tg-root        flat TextGrid folder                      [stress, fp]
--tg-suffix      filename suffix, default ".TextGrid"       [stress, fp]
--copy           copy matching audio + TextGrid to --out-dir
--dry-run        preview --copy actions instead of copying
--limit          cap the number of matches listed/copied
--out-dir        destination folder, default ./examples
--gender         M or F, filters by Speaker_gender
--out-jsonl      shortlist output path                     [doublets]
--word           target surface word / word filter          [stress, fp]
--upos           restrict to a UPOS tag, e.g. VERB           [stress]
--stress         stress position to list/copy                [stress]
--min-fp         minimum filled-pause count, default 1        [fp]
--fp-annot-dirs  one or more annotated-TextGrid folders       [fp-annot]
--label          target label in the fp-annotation tier       [fp-annot]
--fp-annot-glob  glob for TextGrids, default "*.TextGrid"      [fp-annot]

Example invocations
--------------------
python find_tg_examples.py --mode doublets --jsonl ParlaSpeech-HR.v3.jsonl --out-jsonl doublets.jsonl

python find_tg_examples.py --mode stress --jsonl ParlaSpeech-HR.v3.jsonl --word uspostavi --upos VERB --stress 2 --audio-root audio/ --tg-root textgrids_flat/ --copy --limit 10 --out-dir examples/

python find_tg_examples.py --mode fp --jsonl ParlaSpeech-HR.v3.jsonl --min-fp 2 --gender F --audio-root audio/ --tg-root textgrids_flat/ --copy

python find_tg_examples.py --mode fp-annot --fp-annot-dirs annot_A/ annot_B/ --label FP
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

def iter_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def passes_gender(speaker_info: dict, gender_filter: str | None) -> bool:
    if not gender_filter:
        return True
    return (speaker_info or {}).get("Speaker_gender") == gender_filter


def extract_word_texts(row: dict) -> list[str]:
    """Lowercased surface word tokens, schema-agnostic (v3 words_align vs
    v1-style flat 'words' list of strings)."""
    words_align = row.get("words_align")
    if words_align:
        return [(w.get("text") or "").lower() for w in words_align]
    words = row.get("words")
    if words and isinstance(words[0], str):
        return [w.strip(",.!?„“").lower() for w in words]
    return []


def resolve_audio(audio_root: Path | None, raw_audio_field: str) -> Path | None:
    """raw_audio_field like '<hash>/<stem>.flac'. Tolerates .wav/.flac skew."""
    if not audio_root or not raw_audio_field:
        return None
    p = Path(audio_root) / raw_audio_field
    if p.exists():
        return p
    for ext in (".wav", ".flac", ".WAV", ".FLAC"):
        alt = p.with_suffix(ext)
        if alt.exists():
            return alt
    return None


def resolve_textgrid(tg_root: Path | None, raw_audio_field: str, tg_suffix: str) -> Path | None:
    """Flat folder, filename = '{audio_stem}{tg_suffix}'."""
    if not tg_root or not raw_audio_field:
        return None
    stem = Path(raw_audio_field).stem
    p = Path(tg_root) / f"{stem}{tg_suffix}"
    return p if p.exists() else None


def copy_pair(audio_path: Path | None, tg_path: Path | None, out_dir: Path, dry_run: bool) -> None:
    actions = []
    if audio_path:
        actions.append(("audio", audio_path, out_dir / audio_path.name))
    if tg_path:
        actions.append(("textgrid", tg_path, out_dir / tg_path.name))
    if not actions:
        return
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    for kind, src, dest in actions:
        if dry_run:
            print(f"    [dry-run] would copy {kind}: {src} -> {dest}")
        else:
            shutil.copy2(src, dest)
            print(f"    copied {kind}: {src} -> {dest}")


# --------------------------------------------------------------------------- #
# Mode: doublets
# --------------------------------------------------------------------------- #

def run_doublets(args: argparse.Namespace) -> None:
    word_stress_counts: dict[str, Counter] = defaultdict(Counter)
    word_total: Counter = Counter()

    for row in iter_jsonl(args.jsonl):
        words_align = row.get("words_align") or []
        primary_stress = row.get("primary_stress") or []
        if not words_align or not primary_stress:
            continue
        stress_by_idx = {
            ps["words_align_idx"]: ps["stress"]
            for ps in primary_stress
            if ps.get("words_align_idx") is not None
        }
        for i, w in enumerate(words_align):
            text = (w.get("text") or "").strip()
            if not text:
                continue
            word_total[text] += 1
            if i in stress_by_idx:
                word_stress_counts[text][stress_by_idx[i]] += 1

    results = []
    for word, counter in word_stress_counts.items():
        n_positions = len(counter)
        if n_positions < 2:
            continue
        total = sum(counter.values())
        mode_count = counter.most_common(1)[0][1]
        results.append({
            "word": word,
            "n_instances_with_stress": total,
            "n_instances_total": word_total[word],
            "n_distinct_positions": n_positions,
            "stress_counts": dict(counter),
            "minority_count": total - mode_count,
        })

    results.sort(key=lambda r: (r["n_distinct_positions"], r["minority_count"]), reverse=True)

    if args.limit:
        results = results[: args.limit]

    if args.out_jsonl:
        with open(args.out_jsonl, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {len(results)} doublet candidate(s) -> {args.out_jsonl}")
    else:
        print(f"{len(results)} doublet candidate(s) (top 20 shown; pass --out-jsonl to save all):")
        for r in results[:20]:
            print(f"  {r['word']}: {r['stress_counts']}  (minority={r['minority_count']})")


# --------------------------------------------------------------------------- #
# Mode: stress
# --------------------------------------------------------------------------- #

def run_stress(args: argparse.Namespace) -> None:
    target = args.word.strip().lower()

    matches = []
    position_counts: Counter = Counter()
    total_seen = 0

    for row in iter_jsonl(args.jsonl):
        words_align = row.get("words_align") or []
        if not words_align:
            continue
        primary_stress = row.get("primary_stress") or []
        stress_by_idx = {
            ps["words_align_idx"]: ps["stress"]
            for ps in primary_stress
            if ps.get("words_align_idx") is not None
        }
        ling = row.get("linguistic_annotation") or []
        upos_by_words_idx = {
            la["words_idx"]: la.get("upos")
            for la in ling
            if la.get("words_idx") is not None
        }

        speaker_info = row.get("speaker_info") or {}
        if not passes_gender(speaker_info, args.gender):
            continue

        for i, w in enumerate(words_align):
            text = (w.get("text") or "").strip().lower()
            if text != target:
                continue
            total_seen += 1
            upos = upos_by_words_idx.get(w.get("words_idx"))
            if args.upos and upos != args.upos:
                continue
            stress = stress_by_idx.get(i)
            position_counts[stress] += 1
            matches.append({"row": row, "words_align_idx": i, "stress": stress, "upos": upos})

    filt_desc = " ".join(
        f"--{k} {v}" for k, v in (("upos", args.upos), ("gender", args.gender)) if v
    )
    print(f"'{args.word}': {total_seen} raw occurrence(s) in corpus" + (f" (filters: {filt_desc})" if filt_desc else "") + ".")

    if not matches:
        print("no matching instances after filters — nothing to list/copy.")
        return

    print(f"{len(matches)} instance(s) pass all filters. Stress-position breakdown:")
    for pos, count in sorted(position_counts.items(), key=lambda kv: (kv[0] is None, kv[0])):
        label = "no-stress-data" if pos is None else f"position {pos}"
        print(f"  {label}: {count}")

    distinct_positions = {p for p in position_counts if p is not None}
    if len(distinct_positions) < 2:
        print(f"  note: '{args.word}' shows only {len(distinct_positions)} distinct stress position(s) here — not a doublet.")

    if args.stress is None:
        print("\npass --stress <n> to list/copy instances at a specific position.")
        return

    selected = [m for m in matches if m["stress"] == args.stress]
    if args.limit:
        selected = selected[: args.limit]
    print(f"\n{len(selected)} instance(s) at stress position {args.stress}" + (f" (limited to {args.limit})" if args.limit else "") + ":")

    for m in selected:
        row = m["row"]
        print(f"  {row['id']}  audio={row.get('audio')}")
        if args.copy:
            audio_path = resolve_audio(args.audio_root, row.get("audio"))
            tg_path = resolve_textgrid(args.tg_root, row.get("audio"), args.tg_suffix)
            if audio_path is None:
                print("    ! audio not found, skipping copy")
                continue
            copy_pair(audio_path, tg_path, args.out_dir, args.dry_run)


# --------------------------------------------------------------------------- #
# Mode: fp
# --------------------------------------------------------------------------- #

def run_fp(args: argparse.Namespace) -> None:
    matches = []
    for row in iter_jsonl(args.jsonl):
        fps = row.get("filled_pauses") or []
        if len(fps) < args.min_fp:
            continue

        speaker_info = row.get("speaker_info") or {}
        if not passes_gender(speaker_info, args.gender):
            continue

        if args.word:
            texts = extract_word_texts(row)
            if args.word.strip().lower() not in texts:
                continue

        matches.append(row)

    filt_desc = " ".join(
        f"--{k} {v}" for k, v in (("word", args.word), ("gender", args.gender)) if v
    )
    print(f"{len(matches)} utterance(s) with >= {args.min_fp} filled pause(s)" + (f" (filters: {filt_desc})" if filt_desc else "") + ".")

    if args.limit:
        matches = matches[: args.limit]

    for row in matches:
        print(f"  {row['id']}  n_fp={len(row.get('filled_pauses') or [])}  audio={row.get('audio')}")
        if args.copy:
            audio_path = resolve_audio(args.audio_root, row.get("audio"))
            tg_path = resolve_textgrid(args.tg_root, row.get("audio"), args.tg_suffix)
            if audio_path is None:
                print("    ! audio not found, skipping copy")
                continue
            copy_pair(audio_path, tg_path, args.out_dir, args.dry_run)


# --------------------------------------------------------------------------- #
# Mode: fp-annot
# --------------------------------------------------------------------------- #

def run_fp_annot(args: argparse.Namespace) -> None:
    from praatio import textgrid as tgio  # lazy import — only this mode needs it

    hit_count = 0
    for d in args.fp_annot_dirs:
        d = Path(d)
        if not d.exists():
            print(f"! directory not found, skipping: {d}")
            continue
        for tg_path in sorted(d.rglob(args.fp_annot_glob)):
            try:
                tg = tgio.openTextgrid(str(tg_path), includeEmptyIntervals=False)
            except Exception as e:
                print(f"! failed to read {tg_path}: {e}")
                continue

            tier_names = getattr(tg, "tierNames", None) or getattr(tg, "tierNameList", None) or []
            if "fp-annotation" not in tier_names:
                continue
            tier = tg.getTier("fp-annotation") if hasattr(tg, "getTier") else tg.tierDict["fp-annotation"]
            entries = getattr(tier, "entries", None) or getattr(tier, "entryList", None) or []

            for entry in entries:
                start, end, label = entry[0], entry[1], entry[2]
                if label == args.label:
                    hit_count += 1
                    print(f"{tg_path}\t{start:.2f}-{end:.2f}")

    print(f"\n{hit_count} hit(s) for label '{args.label}'.")


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Locate ParlaSpeech example utterances by primary-stress doublets, "
                     "target word, filled-pause count, or human-annotated FP label.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--mode", required=True, choices=["doublets", "stress", "fp", "fp-annot"])

    p.add_argument("--jsonl", type=Path, help="Path to ParlaSpeech JSONL (doublets/stress/fp).")
    p.add_argument("--audio-root", type=Path, help="Root of nested <hash>/<stem>.wav|flac audio.")
    p.add_argument("--tg-root", type=Path, help="Flat folder of TextGrids (stress/fp modes).")
    p.add_argument("--tg-suffix", default=".TextGrid",
                    help="Suffix appended to audio stem when resolving in --tg-root, "
                         "e.g. '.align.TextGrid', '.pause.TextGrid', '.stress.TextGrid'.")

    p.add_argument("--copy", action="store_true", help="Copy matching audio + TextGrid into --out-dir.")
    p.add_argument("--dry-run", action="store_true", help="With --copy, print planned actions instead of copying.")
    p.add_argument("--limit", type=int, default=None, help="Cap the number of matches listed/copied.")
    p.add_argument("--out-dir", type=Path, default=Path("examples"), help="Destination for --copy. Default: ./examples")

    p.add_argument("--gender", choices=["M", "F"], help="Filter by Speaker_gender.")

    p.add_argument("--out-jsonl", type=Path, help="[doublets] Path to write ranked doublet shortlist.")

    p.add_argument("--word", help="[stress] Target surface word. [fp] optional word-containment filter.")
    p.add_argument("--upos", help="[stress] Restrict to a UPOS tag (e.g. VERB, NOUN).")
    p.add_argument("--stress", type=int, help="[stress] Primary-stress syllable position to list/copy.")

    p.add_argument("--min-fp", type=int, default=1, help="[fp] Minimum filled-pause count per utterance. Default: 1.")

    p.add_argument("--fp-annot-dirs", nargs="+", type=Path, help="[fp-annot] One or more folders of human-annotated TextGrids.")
    p.add_argument("--label", help="[fp-annot] Target label inside the 'fp-annotation' tier (e.g. FP, F, O).")
    p.add_argument("--fp-annot-glob", default="*.TextGrid", help="[fp-annot] Glob for TextGrids under --fp-annot-dirs. Default: '*.TextGrid'.")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode in ("doublets", "stress", "fp") and not args.jsonl:
        parser.error(f"--mode {args.mode} requires --jsonl")
    if args.mode == "stress" and not args.word:
        parser.error("--mode stress requires --word")
    if args.mode == "fp-annot":
        if not args.fp_annot_dirs:
            parser.error("--mode fp-annot requires --fp-annot-dirs")
        if not args.label:
            parser.error("--mode fp-annot requires --label")
    if args.copy and not args.audio_root:
        parser.error("--copy requires --audio-root")

    {
        "doublets": run_doublets,
        "stress": run_stress,
        "fp": run_fp,
        "fp-annot": run_fp_annot,
    }[args.mode](args)


if __name__ == "__main__":
    main()