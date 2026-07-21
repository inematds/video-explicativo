# 🎬 video-explicativo

Skill do Claude Code que cria **vídeos explicativos completos em PT-BR** a partir de um assunto — roteiro, narração TTS local, cenas animadas dark premium, captions e CTA do INEMA.CLUB, nos formatos **16:9** (YouTube) e **9:16** (Shorts/Reels).

Stack: [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML→MP4, Chrome headless + FFmpeg) + narração local com a voz `bella` (inemavox), Kokoro `pf_dora` como fallback. **Tudo roda na máquina, sem chave de API.**

- 📖 **Guia de uso:** https://inematds.github.io/video-explicativo/guia/
- 🎓 **Curso sobre a skill:** https://inematds.github.io/skill-video-explicativo/

## O que ela faz

O fluxo tem 8 etapas, sempre nesta ordem:

**Roteiro → Revisão de texto → Projeto → Fontes → Narração → Composição → Validar → Render**

O nº de cenas é **dinâmico** (sai do roteiro, range 4–12 de conteúdo + a CTA), o timing é **fonte única** (a duração real de cada WAV deriva os `data-start/duration` e os tempos dos tweens), e o mesmo gerador escreve os dois formatos (`--vertical` para o 9:16, com safe zones e título persistente de 2 linhas).

## Estrutura

```
skills/video-explicativo/
  SKILL.md                        # a skill: fluxo, plano de cenas, regras de ouro
  CHANGELOG.md                    # histórico de versões (v1.yy.xxx)
  scripts/
    narration-template.sh         # gera os WAVs (bella/inemavox → fallback Kokoro)
    fetch-fonts.mjs               # baixa Sora/Inter/JetBrains Mono como .woff2 local
    composition-template.mjs      # gerador data-driven (SCENES[] + CTA) → index.html
  references/
    pipeline.md                   # pipeline detalhado (projeto, roteiro, timing, render)
    house-style.md                # paleta dark premium âmbar + tipografia
    motion.md                     # vocabulário de movimento M.* + catálogo de transições
    safe-zones.md                 # zonas da UI dos apps no 9:16
    clips-midia.md                # vídeo/imagem/música, scrim/blur/painel, ducking
    revisao-texto.md              # checklist de acentuação + léxico de inglês fonético
    gotchas.md                    # pegadinhas do HyperFrames
    sem-gpu.md                    # rodar sem GPU: edge-tts/Kokoro + imagens via Agnes AI
```

## Instalar

Copie a pasta da skill para as skills do Claude Code:

```bash
cp -r skills/video-explicativo ~/.claude/skills/
```

Depois é só pedir: *"faz um vídeo explicativo sobre X"*.

## Pré-requisitos

- Node 22+ e FFmpeg (no git-bash use `ffmpeg -nostdin`)
- Chrome headless do HyperFrames: `npx hyperframes browser ensure`
- TTS: inemavox (voz `bella`); fallback Kokoro — `pip install kokoro-onnx soundfile`
- Diagnóstico: `npx hyperframes doctor`

### Sem GPU?

O render nunca precisou de GPU — só a narração default (inemavox/chatterbox) e a geração de
imagem local (flux2-klein) pedem. Substitutos diretos:

- **Narração:** `edge-tts` (nuvem, sem chave) ou **Kokoro** (offline, CPU). Em ambos, **liste e
  escute as vozes antes** de gerar o vídeo inteiro (`edge-tts --list-voices | grep pt-BR`;
  Kokoro PT: `pf_dora`, `pm_alex`, `pm_santa`).
- **Imagens:** **Agnes AI** via `~/projetos/imagens-agnes/gerar.py` (US$ 0, prompt em inglês,
  `size` em pixels, máx. 2 refs) — ou o **fallback SVG**, que dispensa rede e custo.

Receitas completas e regras medidas: [`references/sem-gpu.md`](skills/video-explicativo/references/sem-gpu.md).

## Saída

Todo o conteúdo de um vídeo (projeto, assets, áudios, `index.html` e os MP4 finais) vive numa pasta única: `~/projetos/output/<nome>/`. Um arquivo por formato — `<nome>-16x9.mp4` e `<nome>-9x16.mp4` — e só.

---

Conteúdo do [INEMA.CLUB](https://inema.club) · [PRO](https://inema.pro)
