#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
mkdir -p audio txt

# ============================================================
#  Voz da narração (1.12.3) — 100% local.
#  DEFAULT: inemavox engine `chatterbox` + voz `nei` (conteúdo INEMA narrado pelo Nei).
#  VOZ=rachel para a voz padrão global (inglesa: ouvir uma amostra em PT antes do vídeo inteiro).
#  FALLBACK: Kokoro pf_dora (só se o inemavox falhar).
#  NUNCA chatterbox-vc: ele gera a fala no Edge TTS (serviço em nuvem).
# ============================================================
INEMAVOX="${INEMAVOX:-$HOME/projetos/inemavox/tts_direct.py}"
VOZ="${VOZ:-nei}"
REF="${REF:-$HOME/projetos/timesmkt3/media/voice-refs/$VOZ.wav}"
TTS_PY="${TTS_PY:-python3}"
ENGINE="chatterbox"
KOKORO_VOICE="${KOKORO_VOICE:-pf_dora}"

write() { printf '%s\n' "$2" > "txt/$1.txt"; }

# ---- Exemplo (forma-fala revisada): substitua pelos textos das SUAS cenas ----
write s1 "O que são, de verdade, as Skills no Claude Code? Em poucos minutos você vai entender, do princípio mais básico até o uso avançado. E o melhor: sem escrever uma única linha de código."
write s2 "Comece pelo essencial. Uma Skill é só uma pasta com um arquivo chamado SKILL ponto M D. Dentro dele, instruções em Markdown que ensinam o Claude a fazer algo específico: criar vídeos, revisar código, desenhar interfaces. É conhecimento empacotado."
write s3 "Todo SKILL ponto M D começa com duas linhas essenciais: name e description. A descrição é a parte mais importante de todas. É o que o Claude lê para decidir quando usar aquela skill. Quanto mais clara e específica, melhor o gatilho."
write s4 "E aqui está o conceito-chave: divulgação progressiva. O Claude não carrega tudo de uma vez. Na memória fica sempre só o nome e a descrição. Quando a tarefa combina, ele abre o SKILL ponto M D completo. E só se precisar de mais detalhe, ele lê os arquivos de referência. Assim o contexto fica leve e rápido."
write s5 "Onde elas vivem? Na pasta ponto claude, barra skills, do seu projeto. Ou na sua pasta global, para usar em qualquer lugar. Instalar é tão simples quanto copiar a pasta, ou rodar um comando."
write s6 "No nível avançado, uma Skill é muito mais que texto. Ela pode trazer scripts que o Claude executa, paletas, templates e arquivos de referência carregados sob demanda. Você empacota um fluxo de trabalho inteiro, não só uma dica."
write s7 "Quer um exemplo real? Este próprio vídeo. Ele foi inteirinho construído por uma Skill chamada HyperFrames, que ensinou o Claude a transformar HTML em vídeo. Uma skill, um fluxo, um resultado."
write s8 "Skills transformam o Claude Code num especialista sob medida. Comece simples, com um SKILL ponto M D. Depois evolua. Agora é com você."

# ---- Geração: inemavox chatterbox local → fallback Kokoro ----
gen() {  # gen s1
  local id="$1" tmp
  tmp="$(mktemp -d)"
  if [ -f "$REF" ] && "$TTS_PY" "$INEMAVOX" \
        --text "$(cat "txt/$id.txt")" --lang pt \
        --engine "$ENGINE" --ref "$REF" --outdir "$tmp" >"$tmp/log" 2>&1 \
        && [ -f "$tmp/generated.wav" ]; then
    mv -f "$tmp/generated.wav" "audio/$id.wav"
    # o chatterbox já gravou silêncio "com sucesso" no passado: medir o volume
    mean=$(ffmpeg -nostdin -i "audio/$id.wav" -af volumedetect -f null - 2>&1 | sed -n 's/.*mean_volume: \(-\?[0-9.]*\) dB/\1/p')
    echo "$id: $VOZ (inemavox chatterbox) mean=${mean}dB"
    awk -v m="${mean:--99}" 'BEGIN{exit !(m < -50)}' && echo "  !! $id parece MUDO — regenerar"
  else
    echo "$id: inemavox indisponível -> fallback Kokoro $KOKORO_VOICE"
    npx -y hyperframes tts "txt/$id.txt" --voice "$KOKORO_VOICE" --speed 0.98 --output "audio/$id.wav" >/dev/null 2>&1
  fi
  rm -rf "$tmp"
}

for f in $(ls txt/s*.txt 2>/dev/null | sort -V); do
  id="$(basename "$f" .txt)"
  echo "=== gerando $id ==="
  gen "$id"
done

echo "=== durações (alimente o campo audio de cada cena no build-index.mjs) ==="
for f in $(ls audio/s*.wav 2>/dev/null | sort -V); do
  id="$(basename "$f" .wav)"
  d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f" 2>/dev/null)
  echo "$id: ${d}s"
done
