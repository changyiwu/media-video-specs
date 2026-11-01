# 用 ComfyUI（本機或別台電腦）生成一段 MiniMax H3 影片片段，給社群科普片當素材。什麼時候用見 specs/03 6.6、GOTCHAS D-15～D-17
# 執行（在 repo 根目錄；只用 Python 標準函式庫，不必裝進 H3 的環境）：
#   python tools/h3_runner.py --check [--comfy URL]                    # 伺服器、節點、模型檔都在嗎
#   python tools/h3_runner.py spec.json --out <資料夾> --dry-run       # 只組 prompt.txt 與 workflow_api.json，不連伺服器
#   python tools/h3_runner.py spec.json --out <資料夾>                 # 生成 <資料夾>/clip.mp4、workflow_api.json、meta.json
#   python tools/h3_runner.py --lint prompt.txt [--duration 5]         # 檢查手寫的 prompt（官方六段格式）
# 片段放 output/<主題>/assets/videos/gen/<name>/，spec 放 assets/videos/gen/specs/<name>.json（放進片子的規則見 GOTCHAS D-14）。
#
# Spec（JSON，路徑相對於 spec 檔；prompt 預設讀 <資料夾>/prompt.txt，沒有就從 spec 組）：
#   { "duration": 5.0, "size": [1344, 768], "seed": 2026, "draft": true,
#     "style": "a cinematic, photoreal shot, no text, no logos",
#     "setting": "a dark wet runway at night",
#     "first_frame": "../../../images/gen/hover.png",
#     "subjects": [{"key": "car", "desc": "a sleek unbranded electric hypercar, no badges or text"}],
#     "shots": [{"camera": "The camera holds a static shot on a tripod.", "action": "The car ...", "at": null}],
#     "soundscape": "A heavy thump as the car lands.", "music": "N/A" }
#   duration 換算成 17n+5 格（24 fps）；steps 預設 20（官方模板）；"draft": true 用官方 Lightning LoRA、4 步，快約 4 倍，
#   先看動作，定稿拿掉再跑一次；last_frame 固定最後一格（選配）；lora 接自己的 LoRA：{"name", "strength"} 或一串；sampler 換取樣器。
#
# 組的是 ComfyUI 官方「MiniMax H3 Reference to Video」模板的圖（MiniMaxH3ReferenceToVideo + res_multistep + simple），
# 第一格同時當 <Picture 1> 並固定在第 0 格（MiniMaxH3AddGuide），片段一定從那張圖開始。上傳、排程、下載都走 HTTP API，
# 不需要共用資料夾。模型檔預設是 https://huggingface.co/Comfy-Org/MiniMax-H3 的官方檔案，放進 ComfyUI 的 models/；
# 用 --unet／--clip／--video-vae／--audio-vae／--draft-lora 或環境變數 H3_UNET 等換掉。伺服器：--comfy 或環境變數 COMFY_URL。
# 上游實測（RTX 5090 32 GB）：生成時約用 26 GB VRAM；5 秒 1344x768，draft 76 秒、20 步 297 秒（模型已載入）。
# H3 模型與產出受 MiniMax H3 Community License 約束，使用前先讀。
#
# 改編自 mathruffian-dot/claude-motion-explainer-video 的 h3_runner.py 與 ai_video.py 的 build_prompt（MIT License，
# Copyright (c) 2026 mathruffian-dot）：併成單檔、不依賴別的腳本或 repo。media-short-film 的 h3_shot.py 綁它自己的
# 本機資料夾與短片流程（對白、人聲參考、previs），各 repo 又要能單獨使用，所以不共用。
import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

FPS = 24
SECTIONS = ["subject_definitions", "summary", "retention_analysis", "detailed_description",
            "overall_soundscape", "non_diegetic_music"]
DEFAULTS = {
    "unet": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    "clip": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "video_vae": "minimax_h3_video_vae_int8_convrot.safetensors",
    "audio_vae": "minimax_h3_audio_vae_fp32.safetensors",
    "draft_lora": "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
}
NODES = ["UNETLoader", "CLIPLoader", "VAELoader", "MiniMaxH3ReferenceToVideo", "MiniMaxH3AddGuide", "LoadImage",
         "RandomNoise", "KSamplerSelect", "BasicScheduler", "BasicGuider", "SamplerCustomAdvanced", "VAEDecode",
         "VAEDecodeAudio", "CreateVideo", "SaveVideo", "LoraLoaderModelOnly"]


def frames_for(duration):
    """H3 wants 17n + 5 frames: the smallest such count covering the duration at 24 fps."""
    n = 0
    while 17 * n + 5 < duration * FPS:
        n += 1
    return 17 * n + 5


# ------------------------------------------------------------------------------------------ server
class Comfy:
    def __init__(self, url):
        self.url = url.rstrip("/")

    def get(self, path, timeout=60):
        with urllib.request.urlopen(self.url + path, timeout=timeout) as r:
            return r.read()

    def json(self, path, data=None, timeout=60):
        req = urllib.request.Request(self.url + path, headers={"Content-Type": "application/json"},
                                     data=json.dumps(data).encode() if data is not None else None)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def upload(self, path, name):
        """POST /upload/image (multipart). Returns the LoadImage value "subfolder/name"."""
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n".encode() + Path(path).read_bytes() + b"\r\n"]
        for k, v in (("subfolder", "h3_runner"), ("type", "input"), ("overwrite", "true")):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        body = b"".join(parts) + f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(self.url + "/upload/image", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
        return f'{d["subfolder"]}/{d["name"]}' if d.get("subfolder") else d["name"]

    def options(self, node, field):
        info = self.json(f"/object_info/{node}", timeout=20).get(node, {})
        spec = info.get("input", {}).get("required", {}).get(field)
        if not spec:
            return []
        return spec[0] if isinstance(spec[0], list) else spec[1].get("options", [])


# ------------------------------------------------------------------------------------------ graph
def build_graph(spec, prompt, models, images, tag):
    """images: {"first": LoadImage value or None, "last": ... or None}."""
    w, h = spec.get("size", [1344, 768])
    length = frames_for(float(spec["duration"]))
    steps = spec.get("steps", 20)
    loras = spec.get("lora") or []
    loras = loras if isinstance(loras, list) else [loras]
    if spec.get("draft"):
        loras = [{"name": models["draft_lora"], "strength": 1.0}] + loras
        steps = 4
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": models["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": models["clip"], "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": models["video_vae"]}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": models["audio_vae"]}},
        "6": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
            "clip": ["2", 0], "vae": ["3", 0], "audio_vae": ["4", 0], "prompt": prompt,
            "width": w, "height": h, "length": length, "ref_image_size": "match"}},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": int(spec.get("seed", 42))}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": spec.get("sampler", "res_multistep")}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "audio": ["13", 0], "fps": FPS}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": f"h3_runner/{tag}",
                                                     "format": "mp4", "codec": "h264"}},
    }
    model = ["1", 0]
    for i, lr in enumerate(loras):
        nid = str(80 + i)
        g[nid] = {"class_type": "LoraLoaderModelOnly",
                  "inputs": {"model": model, "lora_name": lr["name"], "strength_model": lr.get("strength", 1.0)}}
        model = [nid, 0]
    g["9"] = {"class_type": "BasicScheduler", "inputs": {"model": model, "scheduler": "simple", "steps": steps, "denoise": 1.0}}
    cond, latent = ["6", 0], ["6", 1]
    if images.get("first"):   # <Picture 1> for the prompt, and pinned at frame 0
        g["5"] = {"class_type": "LoadImage", "inputs": {"image": images["first"]}}
        g["6"]["inputs"]["ref_images.ref_image_0"] = ["5", 0]
        g["40"] = {"class_type": "MiniMaxH3AddGuide", "inputs": {"positive": cond, "latent": latent, "vae": ["3", 0],
                                                                 "image": ["5", 0], "frame_idx": 0}}
        cond = ["40", 0]
    if images.get("last"):    # optional fixed end state
        g["43"] = {"class_type": "LoadImage", "inputs": {"image": images["last"]}}
        g["42"] = {"class_type": "MiniMaxH3AddGuide", "inputs": {"positive": cond, "latent": latent, "vae": ["3", 0],
                                                                 "image": ["43", 0], "frame_idx": -1}}
        cond = ["42", 0]
    g["10"] = {"class_type": "BasicGuider", "inputs": {"model": model, "conditioning": cond}}
    g["11"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["7", 0], "guider": ["10", 0], "sampler": ["8", 0],
                                                                 "sigmas": ["9", 0], "latent_image": latent}}
    return g, length, steps


# ------------------------------------------------------------------------------------------ prompt
def build_prompt(spec):
    """官方六段格式的 MiniMax H3 Ref2VA prompt（第一格 = <Picture 1>）。"""
    subs = spec.get("subjects", [])
    has_first = bool(spec.get("first_frame"))
    defs = [f"<Subject {i + 1}> is {s['desc']}{', visible in <Picture 1>' if has_first and s.get('in_first_frame', True) else ''}."
            for i, s in enumerate(subs)]
    if has_first:
        defs.append("<Picture 1> is the first frame of [Shot 1], fixing the camera position, framing, set layout and lighting.")
    shots = spec["shots"]
    one = len(shots) == 1
    summary = (f"[keyframe completion] The target video is {'one continuous shot' if one else f'{len(shots)} shots'} "
               f"set in {spec.get('setting', 'the scene')}" + (", beginning from <Picture 1>." if has_first else "."))
    keep = [f"<Subject {i + 1}> (appears in [Shot 1]): fully_preserved - identity, shape, colour and materials are retained."
            for i in range(len(subs))]
    if has_first:
        keep.append("<Picture 1> ([Shot 1] first frame): fully_preserved - camera position, framing, set layout and lighting are retained.")
    desc = [f"The target video is in the style of {spec.get('style', 'a cinematic, photoreal shot')}."]
    for k, s in enumerate(shots):
        head = f"[Shot {k + 1}]"
        if k == 0 and has_first:
            head += " The shot begins from <Picture 1>."
        elif s.get("at") is not None:
            m, sec = divmod(float(s["at"]), 60)
            head += f" At {int(m):02d}:{sec:06.3f}, the camera cuts to a new view."
        names = " ".join(f"{subs[i]['desc'].split(',')[0][0].upper()}{subs[i]['desc'].split(',')[0][1:]} is <Subject {i + 1}>."
                         for i in range(len(subs))) if k == 0 else ""
        desc.append(" ".join(x for x in [head, names, s.get("camera", ""), s.get("action", "")] if x))
    body = {
        "subject_definitions": "\n".join(defs),
        "summary": summary,
        "retention_analysis": "\n".join(keep),
        "detailed_description": "\n".join(desc),
        "overall_soundscape": spec.get("soundscape", "Quiet ambient room tone."),
        "non_diegetic_music": spec.get("music", "N/A"),
    }
    return "\n\n".join(f"{k}:\n{body[k]}" for k in SECTIONS) + "\n"


# ------------------------------------------------------------------------------------------ lint
def lint(prompt, duration=None):
    """(errors, warnings) against the official Ref2VA prompt layout (MiniMax-H3 h3-prompt-writing skill)."""
    E, W = [], []
    heads = [(m.group(1), m.group(2), m.start()) for m in re.finditer(r"^([a-z_]+)(:?)[ \t]*$", prompt, re.M)
             if m.group(1) in SECTIONS]
    if [h[0] for h in heads] != SECTIONS:
        E.append(f"sections must be exactly {SECTIONS} in this order; found {[h[0] for h in heads]}")
    E += [f"section '{n}' must end with a colon" for n, colon, _ in heads if not colon]
    body = {}
    for i, (n, _, p) in enumerate(heads):
        end = heads[i + 1][2] if i + 1 < len(heads) else len(prompt)
        body[n] = prompt[p:end].split("\n", 1)[1] if "\n" in prompt[p:end] else ""
    defs = body.get("subject_definitions", "")
    defined = set(re.findall(r"^(<(?:Subject|Picture|Video|Audio) \d+>) is", defs, re.M))
    defined |= set(re.findall(r"<(?:Picture|Video) \d+>", defs))
    E += [f"label {x} is used but never defined in subject_definitions"
          for x in sorted(set(re.findall(r"<(?:Subject|Picture|Video|Audio) \d+>", prompt))) if x not in defined]
    if prompt.count("<d>") != prompt.count("</d>"):
        E.append("unbalanced <d> dialogue tags")
    for n in ("overall_soundscape", "non_diegetic_music"):
        if "<d>" in body.get(n, ""):
            E.append(f"{n} must not contain dialogue")
    dd = body.get("detailed_description", "")
    shots = re.findall(r"\[Shot (\d+)\]( At (\d+):(\d+\.\d+))?", dd)
    if not shots:
        E.append("detailed_description needs [Shot 1]")
    prev = 0.0
    for k, (num, has_t, mm, ss) in enumerate(shots, start=1):
        if int(num) != k:
            E.append(f"shot numbers must be sequential: [Shot {num}] at position {k}")
        if k > 1:
            if not has_t:
                E.append(f"[Shot {num}] needs 'At MM:SS.mmm,'")
                continue
            t = int(mm) * 60 + float(ss)
            if t <= prev or (duration and t >= duration):
                E.append(f"[Shot {num}] cut time {t}s must increase and stay inside the clip")
            prev = t
    if re.search(r"[一-鿿]", re.sub(r"<d>.*?</d>", "", prompt, flags=re.S)):
        W.append("Chinese outside <d>…</d>: write the prompt in English, keep only spoken lines in Chinese")
    if len(dd.split()) < 40:
        W.append(f"detailed_description is short ({len(dd.split())} words); concrete detail helps")
    return E, W


# ------------------------------------------------------------------------------------------ main
def models_from(a):
    return {k: getattr(a, k) or os.environ.get(f"H3_{k.upper()}") or v for k, v in DEFAULTS.items()}


def check(comfy, models):
    try:
        stats = comfy.json("/system_stats", timeout=10)
    except Exception as e:
        sys.exit(f"連不上 ComfyUI {comfy.url}（{e}）：先啟動它，或用 --comfy http://host:port 指定")
    print(f"ComfyUI {stats.get('system', {}).get('comfyui_version', '?')} at {comfy.url}")
    ok = True
    for n in NODES:
        if not comfy.json(f"/object_info/{n}", timeout=20):
            print(f"  缺節點 {n}：更新 ComfyUI（0.36 起內建 MiniMax H3 節點）")
            ok = False
    have = {"unet": comfy.options("UNETLoader", "unet_name"), "clip": comfy.options("CLIPLoader", "clip_name"),
            "video_vae": comfy.options("VAELoader", "vae_name"), "audio_vae": comfy.options("VAELoader", "vae_name"),
            "draft_lora": comfy.options("LoraLoaderModelOnly", "lora_name")}
    for k, name in models.items():
        found = name in have[k]
        print(f"  {'ok     ' if found else 'MISSING'} {k:10} {name}")
        ok &= found or k == "draft_lora"
    if models["draft_lora"] not in have["draft_lora"]:
        print("  （draft 模式才需要上面這個 LoRA）")
    print("可以生成" if ok else "還不行：缺的模型檔從 https://huggingface.co/Comfy-Org/MiniMax-H3 下載")
    return ok


def main():
    ap = argparse.ArgumentParser(description="用 ComfyUI 生成一段 MiniMax H3 影片片段（說明見檔頭）")
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--prompt", help="prompt file (default <out>/prompt.txt, else built from the spec)")
    ap.add_argument("--first-frame", help="first-frame still (overrides the spec's first_frame; '' = none)")
    ap.add_argument("--comfy", default=os.environ.get("COMFY_URL", "http://127.0.0.1:8188"))
    for k in DEFAULTS:
        ap.add_argument("--" + k.replace("_", "-"), dest=k, help=f"default {DEFAULTS[k]}")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--lint", metavar="PROMPT_FILE")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--timeout", type=float, default=1800, help="seconds to wait for one clip")
    a = ap.parse_args()
    models, comfy = models_from(a), Comfy(a.comfy)

    if a.lint:
        E, W = lint(Path(a.lint).read_text(encoding="utf-8"), a.duration)
        print("\n".join([f"ERROR {x}" for x in E] + [f"WARN  {x}" for x in W] + ["OK" if not E else f"{len(E)} error(s)"]))
        sys.exit(1 if E else 0)
    if a.check:
        sys.exit(0 if check(comfy, models) else 1)
    if not a.spec or not a.out:
        ap.error("要給 spec 與 --out（或 --check／--lint）")

    spec_path = Path(a.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    prompt_file = Path(a.prompt) if a.prompt else out / "prompt.txt"
    if prompt_file.exists():
        prompt = prompt_file.read_text(encoding="utf-8")
    else:
        prompt = build_prompt(spec)
        prompt_file.write_text(prompt, encoding="utf-8")
    E, W = lint(prompt, float(spec["duration"]))
    for x in E + W:
        print(("ERROR " if x in E else "WARN  ") + x)
    if E:
        sys.exit("先修 prompt（見上面的錯誤）")

    first = a.first_frame if a.first_frame is not None else (
        str(spec_path.parent / spec["first_frame"]) if spec.get("first_frame") else "")
    last = str(spec_path.parent / spec["last_frame"]) if spec.get("last_frame") else ""
    for p in (first, last):
        if p and not Path(p).exists():
            sys.exit(f"找不到圖片：{p}")
    tag = f"{out.name}_{int(time.time())}"

    if a.dry_run:
        g, length, steps = build_graph(spec, prompt, models, {"first": first and Path(first).name,
                                                               "last": last and Path(last).name}, tag)
        (out / "workflow_api.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[dry-run] {out / 'workflow_api.json'}  {length} frames, {steps} steps")
        return

    if not check(comfy, models):
        sys.exit(1)
    images = {"first": first and comfy.upload(first, f"{tag}_first{Path(first).suffix}"),
              "last": last and comfy.upload(last, f"{tag}_last{Path(last).suffix}")}
    g, length, steps = build_graph(spec, prompt, models, images, tag)
    (out / "workflow_api.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    t0 = time.time()
    pid = comfy.json("/prompt", {"prompt": g, "client_id": uuid.uuid4().hex})["prompt_id"]
    print(f"[queued] {tag}: {length} frames, {steps} steps, seed {spec.get('seed', 42)}", flush=True)
    while True:
        time.sleep(4)
        hist = comfy.json(f"/history/{pid}", timeout=30)
        if pid in hist:
            break
        if time.time() - t0 > a.timeout:
            sys.exit(f"等了 {a.timeout:.0f} 秒還沒好（prompt {pid} 可能還在 ComfyUI 裡跑）")
    e = hist[pid]
    ok = e.get("status", {}).get("status_str") == "success"
    if ok:
        o = e["outputs"]["15"]
        v = (o.get("videos") or o.get("images") or o.get("gifs"))[0]
        q = urllib.parse.urlencode({"filename": v["filename"], "subfolder": v.get("subfolder", ""), "type": v.get("type", "output")})
        (out / "clip.mp4").write_bytes(comfy.get(f"/view?{q}", timeout=300))
    else:
        print(json.dumps(e.get("status", {}), ensure_ascii=False)[:3000])
    meta = {"ok": ok, "frames": length, "steps": steps, "seed": spec.get("seed", 42), "draft": bool(spec.get("draft")),
            "models": models, "wall_s": round(time.time() - t0, 1), "comfy": comfy.url}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{'ok' if ok else 'FAIL'}] {out / 'clip.mp4'}  {meta['wall_s']} s", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
