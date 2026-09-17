#!/usr/bin/env python3
"""Filler-cut + caption remap for /animate.

Reads a HyperFrames-style flat word transcript ([{text,start,end}, ...]),
drops filler words + long silences, emits:
  - keep_segments.json : [[start,end], ...] on the ORIGINAL timeline (for ffmpeg)
  - captions.json      : [{text,start,end}, ...] on the NEW (tightened) timeline
  - cut_stats.json     : durations before/after

Usage:
  cut_and_caption.py TRANSCRIPT.json OUT_DIR [--start S] [--end S]
                     [--gap 0.55] [--pad 0.12] [--maxwords 7] [--maxchars 40]
"""
import argparse, json, re, sys
from pathlib import Path

FILLER = {
    "um", "umm", "uh", "uhh", "uhm", "er", "err", "erm", "ah", "ahh",
    "hmm", "mmm", "eh", "uh-huh", "mhm",
}
# soft fillers only dropped when standalone-ish; conservative to avoid cutting meaning
SOFT_FILLER_PHRASES = ["you know", "sort of", "kind of"]

def norm(t):
    return re.sub(r"[^a-z\-']", "", t.lower())

def load_words(path, win_start, win_end):
    data = json.loads(Path(path).read_text())
    # accept either flat list or {words:[...]} / {segments:[{words}]}
    if isinstance(data, dict):
        if "words" in data:
            data = data["words"]
        elif "segments" in data:
            data = [w for s in data["segments"] for w in s.get("words", [])]
    words = []
    for w in data:
        txt = w.get("text", w.get("word", ""))
        s = float(w.get("start")); e = float(w.get("end"))
        if txt.strip() == "":
            continue
        if win_start is not None and e < win_start:
            continue
        if win_end is not None and s > win_end:
            continue
        words.append({"text": txt.strip(), "start": s, "end": e})
    return words

def is_filler(word):
    return norm(word["text"]) in FILLER

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript"); ap.add_argument("outdir")
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--gap", type=float, default=0.55, help="silence gap (s) that gets collapsed")
    ap.add_argument("--pad", type=float, default=0.12, help="padding kept around speech (s)")
    ap.add_argument("--maxwords", type=int, default=7)
    ap.add_argument("--maxchars", type=int, default=40)
    args = ap.parse_args()

    words = load_words(args.transcript, args.start, args.end)
    if not words:
        print("no words in window", file=sys.stderr); sys.exit(2)

    kept = [w for w in words if not is_filler(w)]
    dropped = [w for w in words if is_filler(w)]

    # Build keep-intervals on original timeline from kept words + padding.
    # Merge when overlapping OR separated by <= gap (natural pause we keep short).
    intervals = []
    for w in kept:
        s = max(0.0, w["start"] - args.pad); e = w["end"] + args.pad
        if intervals and s - intervals[-1][1] <= args.gap:
            intervals[-1][1] = max(intervals[-1][1], e)
        else:
            intervals.append([s, e])

    # Map original time -> new time (piecewise across kept intervals).
    # new_dur accumulates interval lengths.
    offsets = []  # (orig_start, orig_end, new_start)
    acc = 0.0
    for s, e in intervals:
        offsets.append((s, e, acc))
        acc += (e - s)
    new_total = acc

    def remap(t):
        for s, e, ns in offsets:
            if s <= t <= e:
                return ns + (t - s)
        # if t fell in a removed gap, snap to nearest boundary
        for s, e, ns in offsets:
            if t < s:
                return ns
        return new_total

    # Caption lines from kept words on NEW timeline.
    caps = []
    line = []
    def flush():
        if not line:
            return
        text = " ".join(w["text"] for w in line).strip()
        st = remap(line[0]["start"]); en = remap(line[-1]["end"])
        caps.append({"text": text, "start": round(st, 3), "end": round(en, 3)})
        line.clear()

    for i, w in enumerate(kept):
        line.append(w)
        cur = " ".join(x["text"] for x in line)
        ends_sentence = bool(re.search(r"[.!?]$", w["text"]))
        long_gap_next = (i + 1 < len(kept)) and (kept[i+1]["start"] - w["end"] > args.gap)
        # prefer fuller lines: only break on sentence/gap once the line has some heft
        if (len(line) >= args.maxwords or len(cur) >= args.maxchars
                or (ends_sentence and len(line) >= 4)
                or (long_gap_next and len(line) >= 4)):
            flush()
    flush()

    # merge short orphan captions (<=2 words or <0.7s) into a neighbor for readability
    merged = []
    for c in caps:
        short = (len(c["text"].split()) <= 2) or (c["end"] - c["start"] < 0.7)
        if short and merged and (c["start"] - merged[-1]["end"] < 0.6) and \
           len((merged[-1]["text"] + " " + c["text"]).split()) <= args.maxwords + 2:
            merged[-1]["text"] = (merged[-1]["text"] + " " + c["text"]).strip()
            merged[-1]["end"] = c["end"]
        else:
            merged.append(c)
    caps = merged

    out = Path(args.outdir)
    (out / "keep_segments.json").write_text(json.dumps(intervals, indent=2))
    (out / "captions.json").write_text(json.dumps(caps, indent=2))
    orig_span = (words[-1]["end"] - words[0]["start"])
    stats = {
        "orig_window_span_s": round(orig_span, 2),
        "kept_words": len(kept), "dropped_filler_words": len(dropped),
        "dropped_filler_samples": [w["text"] for w in dropped[:20]],
        "segments": len(intervals),
        "new_total_s": round(new_total, 2),
        "caption_lines": len(caps),
    }
    (out / "cut_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
