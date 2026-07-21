# Rodar sem GPU (e sem inemavox / sem flux2-klein)

O pipeline (HyperFrames + Chrome headless + FFmpeg) **não precisa de GPU**. Só duas peças
do fluxo default puxam hardware/serviço extra:

| Peça | Default da casa | Por que pesa | Alternativa sem GPU |
|---|---|---|---|
| Narração | inemavox voz `bella` (chatterbox-vc) | clone de timbre roda em modelo neural → quer GPU | **edge-tts** (nuvem, 0 GPU) ou **Kokoro** (CPU) |
| Imagens de cena | flux2-klein | difusão local → GPU/VRAM | **Agnes AI** (`imagens-agnes`, US$ 0) ou **fallback SVG** |

Nada mais muda: roteiro, composição, lint/inspect e render seguem idênticos.

---

## 1. Narração sem GPU

### Opção A — edge-tts (mais leve, precisa de internet)
Sintetiza na nuvem da Microsoft, sem chave, sem modelo local. É o caminho mais rápido
para quem só quer o vídeo saindo.

```bash
pip install edge-tts

# 1) VALIDE A VOZ antes de gerar o vídeo inteiro
edge-tts --list-voices | grep pt-BR          # lista as vozes PT-BR disponíveis
# vozes comuns: pt-BR-FranciscaNeural (F), pt-BR-AntonioNeural (M),
#               pt-BR-ThalitaMultilingualNeural (F, multilíngue)

# 2) Faça uma amostra de 1 frase e ESCUTE antes de gerar as N cenas
edge-tts --voice pt-BR-FranciscaNeural \
         --text "Teste de voz para o vídeo explicativo." --write-media amostra.mp3

# 3) Uma cena por vez (o pipeline espera 1 arquivo por cena)
edge-tts --voice pt-BR-FranciscaNeural --text "$(cat cena1.txt)" --write-media s1.mp3
ffmpeg -nostdin -y -i s1.mp3 -ar 24000 -ac 1 assets/audio/s1.wav
```

Ajuste de ritmo/tom (útil para caber na duração da cena): `--rate=-8%`, `--pitch=-2Hz`.

### Opção B — Kokoro (100% offline, CPU)
Modelo ONNX pequeno; roda em CPU em tempo aceitável. Já é o fallback documentado.

```bash
pip install kokoro-onnx soundfile
# vozes PT (lang_code "p"): pf_dora (F), pm_alex (M), pm_santa (M)
```

**Valide a voz do mesmo jeito**: gere uma frase com cada candidata, escute, escolha, e só
então rode as N cenas. Trocar de voz no meio do vídeo é retrabalho garantido.

### Depois de escolher (vale para qualquer engine)
- Um arquivo de áudio **por cena** (`s1`, `s2`, …), mono, 24 kHz.
- Meça a duração real de cada um e alimente o gerador — o timing do vídeo vem do áudio,
  nunca de um chute:
  ```bash
  ffprobe -v error -show_entries format=duration -of csv=p=0 assets/audio/s1.wav
  ```
- Continue usando a **forma-fala** do roteiro (siglas expandidas, inglês fonético). Isso é
  independente de engine — ver [revisao-texto.md](revisao-texto.md).

---

## 2. Imagens sem GPU — Agnes AI

Em vez de gerar difusão local (flux2-klein), use o CLI do projeto **`imagens-agnes`**
(`~/projetos/imagens-agnes/gerar.py`), que chama a API da Agnes AI —
modelo `agnes-image-2.1-flash`, **US$ 0, sem créditos**, nada roda na sua máquina.

```bash
cd ~/projetos/imagens-agnes
python3 gerar.py "a dark premium abstract data landscape, amber accent, cinematic" \
        --ratio 16:9 --size 2K -o ~/projetos/output/<video>/assets/img/s3.png
python3 gerar.py "..." --ratio 9:16 -o s3-vert.png     # versão do Shorts/Reels
python3 gerar.py "..." --ref base.png                  # img2img (1–2 refs)
```

Chave: `AGNES_API_KEY` em `~/projetos/agnes-nei/.env` (o CLI lê sozinho).

### Regras medidas (≈70 chamadas reais — fonte `~/projetos/agnes-nei/NOTAS-API.md`)
- **Prompt em INGLÊS.** Em PT o filtro de conteúdo derruba prompt legítimo com HTTP 400.
- **`size` em pixels explícitos.** Em img2img o `ratio` é ignorado (cai para 1024²); pixels não.
- **Máximo 2 referências.** 3+ satura; 5 vira confete e o prompt é ignorado.
- **Referência ≤ 10 MB** (uma PNG 4K de 23 MB é rejeitada).
- **Retry com backoff**: ~34% das chamadas voltam 503; o `gerar.py` já tenta 6 vezes.
- **Baixe na hora**: a URL de saída é temporária.

### Defeitos do modelo (e como evitar)
- Forte em **cenário/paisagem**, fraco em **personagem** — para vídeo explicativo isso é ótimo,
  já que a maioria dos planos é fundo/abstrato.
- **Texto denso vira sopa de letras.** Não peça parágrafos na imagem; título curto e grande
  funciona, e ainda assim confira a grafia à mão.
- Pose **frontal simétrica** dispara duplicação (duas caudas/cabeças). Prefira perfil ou
  três-quartos, e peça no **positivo** (`exactly one tail`) — negar ("no two tails") piora.
- O estilo sequestra o assunto ("futurista" prateou um esquilo ruivo): reforce o atributo
  que importa no prompt.

### Se nem Agnes estiver disponível
O fallback **SVG inline** continua valendo e é o caminho mais barato de todos — sem rede,
sem GPU, sem custo. Ver [clips-midia.md](clips-midia.md) ("Fallback SVG"). Todo o
house-style do vídeo já é vetorial/CSS; imagem é reforço, não requisito.

---

## Checklist de quem instala numa máquina sem GPU
1. `node -v` (22+), `ffmpeg -nostdin -version`, `npx hyperframes browser ensure`, `npx hyperframes doctor`.
2. Escolher a engine de TTS: `edge-tts` (rede) **ou** `kokoro-onnx` (offline/CPU).
3. **Listar e testar as vozes** — gerar 1 frase de amostra e escutar antes de fechar o vídeo.
4. Imagens: `AGNES_API_KEY` no `.env` do `agnes-nei` **ou** assumir o fallback SVG.
5. Sem GPU, o único gargalo é o render do Chrome headless — use `--quality draft` para
   conferir e só depois `high` para entregar.
