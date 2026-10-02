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
    key = lambda p: int(re.sub(r"\D", "", p.stem) or 0)
    wavs = sorted((proj / "assets/audio").glob("s*.wav"), key=key)
    txts = sorted((proj / "assets/txt").glob("s*.txt"), key=key)
    if not wavs:
        sys.exit(f"nenhum assets/audio/sN.wav em {proj}")
    # inventário: toda cena com texto precisa de WAV e vice-versa (cena muda ou áudio órfão reprovam)
    sem_wav = sorted({t.stem for t in txts} - {w.stem for w in wavs}, key=lambda n: int(n[1:]))
    sem_txt = sorted({w.stem for w in wavs} - {t.stem for t in txts}, key=lambda n: int(n[1:]))
    if sem_wav or sem_txt:
        print(f"⚠️  inventário: sem WAV {sem_wav or '-'} · sem TXT {sem_txt or '-'}")
    # silêncio: WAV com volume médio abaixo de -50 dB é mudo (o chatterbox já gravou silêncio "com sucesso")
    mudos = []
    for w in wavs:
        r = subprocess.run(["ffmpeg", "-nostdin", "-i", w, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
        m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
        if not m or float(m.group(1)) < -50:
            mudos.append(w.stem)
    if mudos:
        print(f"⚠️  mudos (volume < -50 dB): {mudos}")
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
        # termos críticos: palavras curtas que mudam o sentido (ia, nei, não, sem, só, zero…) contam sempre
        CRIT = {"ia", "nei", "nao", "sem", "so", "zero", "gratis", "club", "inema"}
        rel = [w for w in wn if len(w) > 3 or w in CRIT]
        faltam = [w for w in rel if w not in gn]
        crit_faltam = [w for w in faltam if w in CRIT]
        rep = len(gn) > 4 and (gn[-2:] == gn[-4:-2] or gn[-1] == gn[-2])
        flag = (not gn) or (not wn) or rep or bool(crit_faltam) or (rel and len(faltam) / max(1, len(rel)) > 0.25)
        suspeitas += bool(flag)
        print(f"{'⚠️ ' if flag else '✅'} {name}\n   roteiro: {want}\n   ouviu:   {got or '(nada)'}")
        if faltam:
            print(f"   sumiram/trocadas: {', '.join(faltam[:12])}")
        if rep:
            print("   repetição no fim (balbucio do TTS?) — gere outro take")
    print(f"\n{suspeitas} cena(s) suspeita(s) de {len(bounds)}. Mesmo sem suspeitas: o usuário ouve antes do render final.")
    sys.exit(1 if (suspeitas or sem_wav or sem_txt or mudos) else 0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
