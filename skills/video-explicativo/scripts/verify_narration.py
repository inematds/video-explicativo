#!/usr/bin/env python3
"""Confere a narração por transcrição LOCAL (inemavox transcrever_v1, Whisper large-v3). Sem API.

Uso: python3 verify_narration.py <projeto>   (lê <projeto>/assets/audio/sN.wav e assets/txt/sN.txt)

Imprime, por cena, o texto esperado (forma-fala) e o que o Whisper ouviu, e marca as cenas suspeitas:
palavras do roteiro que sumiram, palavras repetidas no fim (balbucio do TTS) ou transcrição vazia.
AJUDA, NÃO APROVA: o Whisper pode ouvir certo uma palavra mal pronunciada e errar uma certa.
O usuário ouve o áudio antes do render final.

Detalhes medidos (28/09/2026): o Whisper descarta texto repetido idêntico (compression_ratio), por isso
cada WAV é separado por 2 s de silêncio e as cenas nunca são frases idênticas.
"""
import json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path

GAP = 2.0
INEMAVOX = Path.home() / "projetos/inemavox"


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", s)


def main(proj):
    proj = Path(proj).resolve()
    wavs = sorted((proj / "assets/audio").glob("s*.wav"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    if not wavs:
        sys.exit(f"nenhum assets/audio/sN.wav em {proj}")
    tmp = Path(tempfile.mkdtemp(prefix="verify-narr-"))
    sil = tmp / "sil.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                    "-t", str(GAP), sil], check=True)
    parts, bounds, t = [], [], 0.0
    for w in wavs:
        c = tmp / w.name
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", w, "-ar", "16000", "-ac", "1", c], check=True)
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c]))
        bounds.append((t, t + d, w.stem)); t += d + GAP
        parts += [c, sil]
    (tmp / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    allwav = tmp / "all.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", tmp / "list.txt", allwav], check=True)
    r = subprocess.run(["python3", "transcrever_v1.py", "--in", allwav, "--outdir", tmp / "t", "--whisper-model", "large-v3", "--src", "pt"],
                       cwd=INEMAVOX, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("transcrição falhou: " + r.stderr[-500:])
    segs = json.loads((tmp / "t/transcript.json").read_text())
    heard = {name: [] for _, _, name in bounds}
    for s in segs:
        mid = (s["start"] + s["end"]) / 2
        for a, b, name in bounds:
            if a - 0.5 <= mid <= b + 0.5:
                heard[name].append(s["text"].strip()); break
    suspeitas = 0
    for _, _, name in bounds:
        txtf = proj / "assets/txt" / f"{name}.txt"
        want = txtf.read_text(encoding="utf-8").strip() if txtf.exists() else ""
        got = " ".join(heard[name])
        wn, gn = norm(want), norm(got)
        faltam = [w for w in wn if len(w) > 3 and w not in gn]
        rep = len(gn) > 4 and gn[-2:] == gn[-4:-2]
        flag = (not gn) or rep or (wn and len(faltam) / max(1, len([w for w in wn if len(w) > 3])) > 0.25)
        suspeitas += bool(flag)
        print(f"{'⚠️ ' if flag else '✅'} {name}\n   roteiro: {want}\n   ouviu:   {got or '(nada)'}")
        if faltam:
            print(f"   sumiram/trocadas: {', '.join(faltam[:12])}")
        if rep:
            print("   repetição no fim (balbucio do TTS?) — gere outro take")
    print(f"\n{suspeitas} cena(s) suspeita(s) de {len(bounds)}. Mesmo sem suspeitas: o usuário ouve antes do render final.")
    sys.exit(1 if suspeitas else 0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
