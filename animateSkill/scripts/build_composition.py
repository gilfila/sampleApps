#!/usr/bin/env python3
"""Assemble a HyperFrames talking-head-recut composition (Claude-styled).

Full-bleed 16:9 video (overlay) + word-synced caption band + informative
callout cards. Reads captions.json (new-timeline) and callouts.json, writes
public/index.html.

Usage: build_composition.py WORK_DIR DURATION_SECONDS
"""
import json, sys, html
from pathlib import Path

FPS = 30
W, H = 1920, 1080

def q(t):  # quantize to frame grid
    return round(round(float(t) * FPS) / FPS, 4)

def esc(s):
    return html.escape(str(s), quote=True)

def main():
    work = Path(sys.argv[1]); dur = q(float(sys.argv[2]))
    caps = json.loads((work / "captions.json").read_text())
    callouts_path = work / "callouts.json"
    callouts = json.loads(callouts_path.read_text()) if callouts_path.exists() else []

    # clamp caption/callout ends to duration
    for c in caps:
        c["start"] = max(0.0, q(c["start"])); c["end"] = min(dur, q(c["end"]))
    for c in callouts:
        c["start"] = q(c["start"]); c["end"] = min(dur, q(c["end"]))

    # ---- caption band (timed clips, runtime gates visibility) ----
    cap_html = []
    for i, c in enumerate(caps):
        d = round(max(0.2, c["end"] - c["start"]), 4)
        cap_html.append(
            f'<div class="cap clip" data-card-id="cap-{i:03d}" data-start="{c["start"]:.4f}" '
            f'data-duration="{d:.4f}" data-track-index="3">'
            f'<span class="cap-inner">{esc(c["text"])}</span></div>'
        )
    cap_layer = "\n      ".join(cap_html)

    # ---- callout cards ----
    card_hosts, tl_blocks = [], []
    for c in callouts:
        cid = c["id"]; s = c["start"]; e = c["end"]; d = round(e - s, 4)
        x, y, w, h = c.get("x", 96), c.get("y", 96), c.get("w", 720), c.get("h", 300)
        accent = c.get("accent", "#D2795E")
        kicker = esc(c.get("kicker", "")); title = esc(c.get("title", "")); detail = esc(c.get("detail", ""))
        card_hosts.append(f'''<div class="card-host clip" data-card-id="{cid}" data-start="{s:.4f}" data-duration="{d:.4f}" data-track-index="4" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;visibility:hidden;opacity:0;">
        <div class="card" data-card-id="{cid}">
          <div class="root">
            <div class="callout" style="--accent:{accent};">
              <div class="bar"></div>
              <div class="body">
                {'<div class="kicker">'+kicker+'</div>' if kicker else ''}
                <div class="title">{title}</div>
                {'<div class="detail">'+detail+'</div>' if detail else ''}
              </div>
            </div>
          </div>
        </div>
      </div>''')
        enter = q(s); enter_done = q(s + 0.45)
        exit_start = q(e - 0.4); exit_done = q(e)
        sel = f'.card-host[data-card-id="{cid}"]'
        cardsel = f'.card[data-card-id="{cid}"]'
        tl_blocks.append(f'''
          // {cid}
          tl.set('{sel}', {{ visibility: "visible" }}, {enter});
          tl.fromTo('{sel}', {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }}, {enter});
          tl.fromTo('{cardsel} .bar', {{ scaleY: 0 }}, {{ scaleY: 1, duration: 0.5, ease: "power2.out", transformOrigin: "top" }}, {enter_done});
          tl.to('{sel}', {{ opacity: 0, y: -12, duration: 0.4, ease: "power2.in" }}, {exit_start});
          tl.set('{sel}', {{ visibility: "hidden" }}, {exit_done});''')

    card_hosts_html = "\n      ".join(card_hosts)
    tl_all = "\n".join(tl_blocks)

    doc = f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <style>
      @font-face {{ font-family:"Inter"; src:url("fonts/Inter-400-latin.woff2") format("woff2"); font-weight:400; font-display:block; }}
      @font-face {{ font-family:"Inter"; src:url("fonts/Inter-700-latin.woff2") format("woff2"); font-weight:700; font-display:block; }}
      :root {{
        --cream:#F4F1EA; --card:#FBF9F4; --ink:#26231C; --muted:#6B6558; --clay:#D2795E;
      }}
      * {{ box-sizing:border-box; }}
      html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#000;
        font-family:"Inter", ui-sans-serif, system-ui, sans-serif; }}
      #stage {{ position:relative; width:100%; height:100%; overflow:hidden; }}
      .video-wrapper {{ position:absolute; left:0; top:0; width:1920px; height:1080px; overflow:hidden; }}
      .video-wrapper video {{ width:100%; height:100%; object-fit:cover; }}

      /* caption band */
      .cap {{ position:absolute; left:0; right:0; bottom:64px; display:flex; justify-content:center;
        pointer-events:none; }}
      .cap .cap-inner {{ max-width:1360px; text-align:center; font-weight:700; font-size:44px; line-height:1.25;
        color:var(--ink); background:rgba(244,241,234,0.95); padding:14px 30px; border-radius:16px;
        box-shadow:0 8px 30px rgba(0,0,0,0.30); border:1px solid rgba(0,0,0,0.05);
        letter-spacing:-0.01em; }}

      /* callout card */
      .card-host {{ position:absolute; pointer-events:none; overflow:visible; }}
      .card-host .card, .card-host .root {{ position:relative; width:100%; height:100%; }}
      .callout {{ display:flex; gap:22px; width:100%; height:100%; background:var(--card);
        border:1px solid rgba(0,0,0,0.06); border-radius:20px; padding:28px 32px;
        box-shadow:0 18px 50px rgba(0,0,0,0.28); }}
      .callout .bar {{ flex:0 0 8px; align-self:stretch; background:var(--accent); border-radius:8px; }}
      .callout .body {{ display:flex; flex-direction:column; justify-content:center; gap:10px; }}
      .callout .kicker {{ font-weight:700; font-size:22px; letter-spacing:0.14em; text-transform:uppercase;
        color:var(--accent); }}
      .callout .title {{ font-weight:700; font-size:46px; line-height:1.1; color:var(--ink); letter-spacing:-0.02em; }}
      .callout .detail {{ font-weight:400; font-size:27px; line-height:1.35; color:var(--muted); }}
    </style>
  </head>
  <body>
    <div id="stage" data-composition-id="talking-head-recut" data-start="0" data-duration="{dur:.4f}"
         data-fps="{FPS}" data-width="{W}" data-height="{H}">
      <div class="video-wrapper" id="video-wrap">
        <video id="bg-video" src="input-video.mp4" muted playsinline data-start="0" data-duration="{dur:.4f}" data-track-index="1"></video>
      </div>
      <audio id="source-audio" src="input-video.mp4" data-start="0" data-duration="{dur:.4f}" data-track-index="10" data-volume="1"></audio>

      {cap_layer}

      {card_hosts_html}

      <script src="vendor/gsap.min.js"></script>
      <script>
        (function () {{
          const tl = window.gsap.timeline({{ paused: true }});
{tl_all}
          window.__timelines = window.__timelines || {{}};
          window.__timelines["talking-head-recut"] = tl;
        }})();
      </script>
    </div>
  </body>
</html>
'''
    (work / "public" / "index.html").write_text(doc)
    print(f"wrote index.html: dur={dur}s, captions={len(caps)}, callouts={len(callouts)}")

if __name__ == "__main__":
    main()
