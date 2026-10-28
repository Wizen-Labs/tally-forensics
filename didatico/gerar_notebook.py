"""Gera didatico/aprenda_apuracao_ao_vivo.ipynb, a versão didática (em português) do sistema independente do Colab.

Todo o código fica dentro do notebook, dividido em células pequenas, cada uma precedida de uma explicação.
O comportamento é o mesmo da versão validada em colab/tally_colab.py (FINDINGS P7 a P10).
Rodar: python didatico/gerar_notebook.py
"""

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
celulas = []


def texto(md):
    celulas.append({"cell_type": "markdown", "metadata": {}, "source": md.strip("\n").splitlines(keepends=True)})


def codigo(src):
    celulas.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
                    "source": src.strip("\n").splitlines(keepends=True)})


# =====================================================================================================================
texto(r"""
# Aprenda: apuração ao vivo com Python 🗳️🐍

**Autor:** Eduardo Wizentier · **Desenvolvido com:** Claude Opus 5.5 (Anthropic) · **Dados:** TSE (públicos)

Este caderno é ao mesmo tempo **uma ferramenta** e **uma aula**. Ele faz uma projeção do resultado do 2º turno
presidencial a partir das primeiras urnas apuradas, usando apenas os arquivos públicos do Tribunal Superior Eleitoral
(TSE). Cada pedaço do programa vem precedido de uma explicação: o que ele faz, por que existe e qual tecnologia usa.

> ⚠️ **A projeção é uma estimativa estatística. NÃO é resultado oficial.** O resultado oficial é sempre o do TSE.

## Como usar um notebook
- Um *notebook* é um documento com **células**: algumas têm texto (como esta), outras têm **código Python**.
- Para executar uma célula de código, clique nela e aperte **Shift + Enter**. O resultado aparece logo abaixo.
- As células devem ser executadas **em ordem, de cima para baixo**: as de baixo usam o que as de cima criaram.
- Se algo der errado, use **Ambiente de execução → Reiniciar sessão** e rode de novo desde o início.

## Roteiro
| Parte | Assunto |
|---|---|
| 1 | Por que este projeto existe: a "caixa-preta" e o que dá para verificar |
| 2 | Configurações |
| 3 | As bibliotecas de Python que usamos |
| 4 | **Desafio 1:** baixar rápido sem parecer um robô (nem um ataque) |
| 5 | **Desafio 2:** hash, a "impressão digital" dos arquivos |
| 6 | **Desafio 3:** os dados chegam por município, não por urna |
| 7 | **Desafio 4:** o modelo estatístico, explicado com matemática simples |
| 8 | Montando a base do 1º turno |
| 9 | Acompanhando a apuração ao vivo |
| 10 | Ensaio com o 1º turno |
| 11 | O cartão para a mídia |
| 12 | O laço da noite da eleição |
| 13 | Diagnóstico |
| 14 | O que os testes nos ensinaram (os bugs) |
| 15 | Exercícios |
""")

# =====================================================================================================================
texto(r"""
# Parte 1 · Por que este projeto existe

A urna eletrônica brasileira é muitas vezes chamada de **"caixa-preta"**: o eleitor não recebe um comprovante físico
do voto, então não existe recontagem de papel. Isso gera desconfiança, e desconfiança se combate com **verificação**.

O que dá para verificar **com dados públicos** e um pouco de programação:
- se a **soma** de todos os boletins de urna bate com o resultado oficial;
- se a **ordem e o horário** em que os resultados chegaram deixaram alguma marca estranha;
- se dá para **prever** o resultado final com poucas urnas, o que só funciona se os dados forem coerentes entre si.

O que **não** dá para verificar assim: o que acontece **dentro** de cada urna. Para isso seria preciso o voto impresso
conferido pelo eleitor e uma auditoria por amostragem.

Na auditoria do 1º turno de 2026 (no repositório `github.com/Wizen-Labs/tally-forensics`), a soma dos 499.206
boletins bateu **voto a voto** com o resultado oficial, e as urnas recebidas durante a pausa de 27 minutos se
comportaram exatamente como as vizinhas. Este caderno é a próxima etapa: **acompanhar o 2º turno ao vivo**.

**A lição principal:** quem desconfia de algo e sabe programar pode transformar desconfiança em pergunta testável.
""")

# =====================================================================================================================
texto(r"""
# Parte 2 · Configurações

Aqui ficam todos os "botões" do programa. **Leia os comentários** (o texto depois de `#`): em Python, tudo que vem
depois de `#` é ignorado pelo computador e serve só para explicar.

Os dois ajustes mais importantes:
- `ELEICAO`: `"6257"` é o 1º turno (para testes; os arquivos já são finais) e `"6258"` é o 2º turno, em 25 de outubro.
- `AJUDANTE`: deixe vazio (`""`) se você é o Eduardo. Se você é um ajudante, escreva seu primeiro nome, em
  minúsculas e sem espaço. No modo ajudante o programa é mais leve com o servidor e os cartões saem marcados
  "BACKUP · NÃO PUBLICAR".
""")
codigo(r"""
# ---------------- configurações ----------------
ELEICAO = "6257"           # "6257" = 1º turno 2026 (teste) | "6258" = 2º turno, 25/10/2026
ELEICAO_BASE = "6257"      # o 1º turno serve de base de comparação para o 2º turno
NUM_A, NUM_B = "22", "13"  # números dos candidatos: 22 = Flávio Bolsonaro, 13 = Lula
NOME_A, NOME_B = "Flávio Bolsonaro", "Lula"

INTERVALO_S = 30           # de quantos em quantos segundos o programa consulta o TSE
CARTAO_A_CADA_MIN = 5      # de quantos em quantos minutos salva um cartão para a mídia
HORA_PARAR = "21:00"       # horário de Brasília em que o laço ao vivo para sozinho
AJUDANTE = ""              # "" = Eduardo. Ajudantes: seu primeiro nome, ex.: "pedro"

# limites de "boa educação" com o servidor do TSE (explicados na Parte 4)
CONEXOES = 16              # quantos downloads podem acontecer ao mesmo tempo
MAX_POR_SEGUNDO = 15       # no máximo 15 pedidos por segundo
MAX_MUNICIPIOS_POR_CICLO = 900

if AJUDANTE:               # modo ajudante: mais leve e com marca d'água
    INTERVALO_S, CONEXOES, MAX_POR_SEGUNDO, MAX_MUNICIPIOS_POR_CICLO, CARTAO_A_CADA_MIN = 90, 8, 8, 450, 15
    MARCA_DAGUA = "BACKUP · NÃO PUBLICAR"
else:
    MARCA_DAGUA = None if ELEICAO == "6258" else "SIMULAÇÃO"

MEIA_MARGEM = 0.8          # margem estimada, em pontos percentuais (Parte 7)
print("Configurações carregadas. Eleição:", ELEICAO, "| ajudante:", AJUDANTE or "(não)", "| marca d'água:", MARCA_DAGUA)
""")

texto(r"""
### Onde os dados ficam guardados
No Google Colab, o disco do computador é **apagado** quando a sessão termina. Por isso guardamos tudo no
**Google Drive**. A célula abaixo pede sua autorização para usar o Drive.

Repare no `try` / `except`: é a forma de Python dizer "tente isto; se der um erro deste tipo, faça aquilo". Se o
caderno não estiver rodando no Colab (por exemplo, no seu computador), ele usa uma pasta local.
""")
codigo(r"""
import os
try:
    from google.colab import drive          # só existe dentro do Google Colab
    drive.mount("/content/drive")
    PASTA_COMPARTILHADA = "/content/drive/MyDrive/tally_live_independent"   # ajudantes: o atalho da pasta do Eduardo
except ImportError:
    PASTA_COMPARTILHADA = os.path.abspath("dados_apuracao")                  # fora do Colab: pasta local

PASTA = os.path.join(PASTA_COMPARTILHADA, "helpers", AJUDANTE) if AJUDANTE else PASTA_COMPARTILHADA
os.makedirs(PASTA, exist_ok=True)
print("Os arquivos serão gravados em:", PASTA)
""")

# =====================================================================================================================
texto(r"""
# Parte 3 · As bibliotecas de Python que usamos

Uma **biblioteca** é um conjunto de código pronto, que alguém escreveu e testou, para não precisarmos reinventar a
roda. Algumas já vêm com o Python (a "biblioteca padrão"); outras são instaladas à parte.

| Biblioteca | Vem com o Python? | Para que usamos |
|---|---|---|
| `urllib.request` | sim | fazer pedidos pela internet (baixar arquivos do TSE) |
| `json` | sim | ler os arquivos do TSE, que estão no formato JSON (texto organizado em chaves e valores) |
| `hashlib` | sim | calcular o **hash** (impressão digital) de cada arquivo |
| `gzip` | sim | comprimir os arquivos guardados, para ocupar menos espaço |
| `threading`, `concurrent.futures` | sim | fazer vários downloads **ao mesmo tempo** (em paralelo) |
| `time`, `datetime` | sim | medir tempo, esperar, trabalhar com horários e fusos |
| `pandas` | não (o Colab já tem) | tabelas: juntar, somar e filtrar dados como numa planilha |
| `matplotlib` | não (o Colab já tem) | desenhar gráficos e o cartão para a mídia |

A célula abaixo importa tudo (`import`) e mostra um mini-exemplo de JSON.
""")
codigo(r"""
import gzip, hashlib, json, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd

# mini-exemplo: um pedaço de JSON parecido com o do TSE, transformado em dicionário Python
exemplo = '{"cdabr": "71072", "s": {"ts": "26683", "st": "120"}}'
d = json.loads(exemplo)
print("município:", d["cdabr"], "| seções totais:", d["s"]["ts"], "| seções apuradas:", d["s"]["st"])

BRASILIA = timezone(timedelta(hours=-3))       # o horário oficial da apuração é o de Brasília (UTC-3)
print("Agora em Brasília:", datetime.now(BRASILIA).strftime("%H:%M:%S"))
""")

# =====================================================================================================================
texto(r"""
# Parte 4 · Desafio 1: baixar rápido sem parecer um robô (nem um ataque)

## O problema
O TSE publica, durante a apuração:
- um arquivo de **andamento** por estado (quantas seções de cada município já foram apuradas);
- um arquivo de **resultado** por município: são **5.757** (5.570 no Brasil e cidades no exterior).

Quanto mais rápido baixamos, mais cedo projetamos. Mas um programa que faz centenas de pedidos por segundo a partir
de um único endereço se parece com um **robô** ou com o começo de um **ataque de negação de serviço (DDoS)**, que
tenta derrubar um site sobrecarregando-o. Servidores sérios se defendem disso.

**Aconteceu nos nossos testes:** com 32 downloads simultâneos, o TSE respondeu **4.246 vezes com o código HTTP 429**
("Too Many Requests", isto é, "pedidos demais"). É o servidor pedindo para desacelerar.

## A solução: quatro regras de boa educação
1. **Ritmo máximo:** no máximo 15 pedidos por segundo, somando todos os downloads paralelos.
2. **Respeitar o 429:** se o servidor pedir para esperar, *todos* os downloads param pelo tempo pedido
   (o cabeçalho `Retry-After`; se não vier, 30 segundos).
3. **Pedidos condicionais:** dizemos ao servidor "só me mande se mudou desde a última vez" (cabeçalhos
   `If-None-Match` / `If-Modified-Since`). Se não mudou, ele responde **304** sem enviar o arquivo: rápido e leve.
4. **Prioridade:** se muitos municípios mudaram ao mesmo tempo, baixamos primeiro os de **maior eleitorado**
   (no máximo 900 por ciclo); o resto fica para o ciclo seguinte.

Com isso, nos testes, o número de respostas 429 caiu de 4.246 para **zero**.

## Demonstração (sem acessar o TSE)
A célula abaixo simula 30 "pedidos" com limite de 10 por segundo, usando 8 *threads* (trabalhadores em paralelo).
Repare que, mesmo em paralelo, eles saem espaçados: levam cerca de 3 segundos.
""")
codigo(r"""
class LimiteDeRitmo:
    # Garante no máximo `por_segundo` pedidos por segundo, mesmo com vários threads ao mesmo tempo.
    def __init__(self, por_segundo):
        self.intervalo = 1.0 / por_segundo
        self.proximo = 0.0           # horário em que o próximo pedido pode sair
        self.pausa_ate = 0.0         # usado quando o servidor responde 429
        self.trava = threading.Lock()   # impede que dois threads mexam nos números ao mesmo tempo

    def esperar_vez(self):
        with self.trava:
            inicio = max(time.time(), self.proximo, self.pausa_ate)
            self.proximo = inicio + self.intervalo
        espera = inicio - time.time()
        if espera > 0:
            time.sleep(espera)

    def pausar(self, segundos):
        with self.trava:
            self.pausa_ate = max(self.pausa_ate, time.time() + segundos)

# demonstração: 30 "pedidos" falsos, 8 em paralelo, no máximo 10 por segundo
limite = LimiteDeRitmo(10)
t0 = time.time()
def pedido_falso(i):
    limite.esperar_vez()
    return round(time.time() - t0, 2)
with ThreadPoolExecutor(8) as executor:
    horarios = list(executor.map(pedido_falso, range(30)))
print("segundos em que cada pedido saiu:", horarios)
print(f"30 pedidos levaram {time.time() - t0:.1f} s (esperado: cerca de 3 s)")
""")

texto(r"""
## O "baixador" de verdade
Agora a classe que baixa os arquivos do TSE. Ela junta as quatro regras e mais duas proteções:
- **nenhum erro derruba o programa:** qualquer falha (internet caiu, demora maior que 30 s) vira um registro, e o
  arquivo é tentado de novo no ciclo seguinte;
- **tudo é registrado:** cada pedido vira uma linha no arquivo `fetch_log.jsonl` (horário, endereço, código de
  resposta, hash). É a nossa "cadeia de custódia".

Os códigos de resposta HTTP que você vai ver: **200** = arquivo enviado; **304** = não mudou; **429** = pedidos demais;
**404** = arquivo ainda não existe; **0** = erro de rede (nosso código, não do HTTP).
""")
codigo(r"""
USER_AGENT = {"User-Agent": "tally-forensics-didatico/1.0 (pesquisa)"}   # nos identificamos ao servidor

class Baixador:
    def __init__(self, pasta, conexoes, por_segundo):
        self.pasta = Path(pasta)
        (self.pasta / "blobs").mkdir(parents=True, exist_ok=True)
        self.registro = self.pasta / "fetch_log.jsonl"
        self.conexoes = conexoes
        self.limite = LimiteDeRitmo(por_segundo)
        self.validadores = {}        # url -> (ETag, Last-Modified) da última resposta
        self.conteudos = {}          # url -> último conteúdo lido (já convertido de JSON)
        self.trava = threading.Lock()

    def baixar(self, url):
        self.limite.esperar_vez()                                   # regra 1: ritmo máximo
        cabecalhos = dict(USER_AGENT)
        etag, modificado = self.validadores.get(url, (None, None))
        if etag:
            cabecalhos["If-None-Match"] = etag                      # regra 3: "só se mudou"
        if modificado:
            cabecalhos["If-Modified-Since"] = modificado
        linha = {"t_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "url": url}
        corpo = None
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=30) as resp:
                corpo = resp.read()
                self.validadores[url] = (resp.headers.get("ETag"), resp.headers.get("Last-Modified"))
                linha["status"] = resp.status
        except urllib.error.HTTPError as erro:                      # o servidor respondeu com um código de erro
            linha["status"] = erro.code
            if erro.code == 429:                                    # regra 2: respeitar o pedido de calma
                pedido = (erro.headers or {}).get("Retry-After", "")
                self.limite.pausar(min(int(pedido), 120) if str(pedido).isdigit() else 30)
        except Exception as erro:                                   # qualquer outro problema de rede
            linha.update(status=0, error=f"{type(erro).__name__}: {erro}"[:200])
        if corpo is not None:
            impressao = hashlib.sha256(corpo).hexdigest()           # hash: Parte 5
            dados = json.loads(corpo.decode("utf-8-sig"))
            with self.trava:
                arquivo = self.pasta / "blobs" / f"{impressao}.json.gz"
                if not arquivo.exists():
                    arquivo.write_bytes(gzip.compress(corpo))
                linha["sha256"] = impressao
                self.conteudos[url] = dados
        with self.trava, open(self.registro, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha) + "\n")
        return linha["status"], self.conteudos.get(url)              # 304: devolve o último conteúdo lido

    def baixar_varios(self, urls):
        with ThreadPoolExecutor(self.conexoes) as executor:
            return dict(zip(urls, executor.map(self.baixar, urls)))

print("Classe Baixador pronta.")
""")

# =====================================================================================================================
texto(r"""
# Parte 5 · Desafio 2: hash, a "impressão digital" dos arquivos

Um **hash criptográfico** (como SHA-256 ou SHA-512) transforma qualquer arquivo num número de tamanho fixo, escrito
em hexadecimal. Três propriedades o tornam útil:
1. **Sempre o mesmo:** o mesmo arquivo gera sempre o mesmo hash.
2. **Efeito avalanche:** mudar **uma única letra** muda o hash completamente.
3. **Resistência a colisões:** é inviável, com os computadores atuais, encontrar dois arquivos diferentes com o
   mesmo hash. Para o SHA-256, seria preciso algo como 2¹²⁸ tentativas. Mesmo um computador quântico grande (com o
   algoritmo de Grover) só reduziria a segurança de busca de 2²⁵⁶ para 2¹²⁸, o que continua fora de alcance.

### Como os hashes aparecem neste projeto
- **Arquivos completos de boletim de urna** (publicados pelo TSE depois da eleição): vêm acompanhados de um
  **SHA-512 oficial**. A auditoria confere cada um. Além disso, cada boletim é **assinado digitalmente** pela urna.
- **Arquivos ao vivo da apuração** (os que este caderno baixa): o TSE **não** publica hash junto. Por isso o
  programa **calcula o SHA-256 de cada arquivo recebido** e guarda o arquivo com esse nome. Isso prova, depois,
  exatamente **o que** recebemos e **quando**, e um arquivo guardado não pode ser trocado sem que o nome deixe de bater.

Veja o efeito avalanche:
""")
codigo(r"""
a = "Lula 53879538 votos"
b = "Lula 53879539 votos"          # só o último dígito mudou
print("SHA-256 de a:", hashlib.sha256(a.encode()).hexdigest())
print("SHA-256 de b:", hashlib.sha256(b.encode()).hexdigest())
iguais = sum(x == y for x, y in zip(hashlib.sha256(a.encode()).hexdigest(), hashlib.sha256(b.encode()).hexdigest()))
print(f"caracteres iguais na mesma posição: {iguais} de 64 (por acaso, esperamos cerca de 4)")
""")

# =====================================================================================================================
texto(r"""
# Parte 6 · Desafio 3: os dados chegam por município, não por urna

### O que o TSE publica durante a apuração
| O que | Quando fica disponível |
|---|---|
| Votos **por município** e quantas seções dele já foram apuradas | ~2 minutos depois da última urna do município |
| Votos **por seção / por urna** | **horas depois** (no 1º turno, a partir das 20h30, em lotes) |

No 2º turno de 2022, 99% das urnas já tinham chegado por volta das 20h. Ou seja: **durante a janela útil da projeção
só temos totais por município.**

### Por que isso reduz a precisão
Imagine São Paulo, com 26 mil seções. Às 17h30, digamos que 2.000 já foram apuradas. O TSE nos diz *quantos votos*
essas 2.000 deram, mas **não quais seções** são. As primeiras costumam ser de alguns bairros, não de uma amostra
sorteada da cidade inteira. O modelo tem de **supor** que elas representam a cidade, e essa suposição tem erro.

Com dados **por seção**, cada urna seria comparada com **ela mesma no 1º turno**: a distribuição real, bairro por
bairro, ficaria representada. Os nossos ensaios com o 2º turno de 2022 mediram a diferença:

| Dados disponíveis | Erro típico com 2% a 5% apurado |
|---|---|
| Por seção (urna a urna) | cerca de **±0,1** ponto percentual |
| Por município (o que temos ao vivo) | cerca de **±0,5 a ±0,8** ponto percentual |

**Representatividade geográfica:** como as primeiras urnas não vêm de todo o país (no 1º turno, 26% das primeiras
eram do Paraná), o programa só publica a projeção quando **pelo menos 24 dos 27 estados** já têm dados.
""")

# =====================================================================================================================
texto(r"""
# Parte 7 · Desafio 4: o modelo estatístico

### A ideia em uma frase
Cada município já votou três semanas antes, no 1º turno. Comparamos **a parte já apurada** de cada município com o
que **ela mesma** deu no 1º turno. A diferença ("swing") nos diz como o eleitorado se moveu, e aplicamos esse
movimento à **parte que ainda falta**.

### A matemática, passo a passo
Para cada município *m*:

1. **Fatia de Flávio no 1º turno,** entre os dois candidatos: `s1 = A1 / (A1 + B1)`.
2. **Fração apurada** do eleitorado: `f = eleitores apurados / eleitores totais` (1 quando o município termina).
3. **Swing observado:** quanto Flávio ganhou ou perdeu em relação ao 1º turno, na parte já apurada,
   medido em votos: `swing_votos = A2 − (A2 + B2) × s1`.
4. **Encolhimento (shrinkage):** um município com poucas urnas apuradas dá um swing pouco confiável. Por isso o
   swing de cada município é "puxado" para o swing do estado, e o do estado para o do país:

   `swing_m = (swing_votos_m + k_mun × swing_estado) / (votos_apurados_m + k_mun)`

   É uma **média ponderada**: `k_mun = 2000` funciona como "2.000 votos de opinião prévia". Com poucos votos
   apurados manda o estado; com muitos, manda o próprio município. O mesmo vale do país para o estado,
   com `k_uf = 10000`.
5. **Comparecimento:** do mesmo jeito, estimamos se vai votar mais ou menos gente que no 1º turno (`razão_votos`).
6. **Parte que falta:** `votos_faltantes = (A1 + B1) × (1 − f) × razão_votos` e
   `Flávio_faltante = (s1 + swing_m) × votos_faltantes`.
7. **Total:** `Flávio = apurado + faltante` (o mesmo para Lula), e a projeção é `Flávio / (Flávio + Lula)`.

O exterior entra como se fosse mais um estado. Antes de corrigirmos isso, os votos do exterior ainda não lidos
contavam como zero (Parte 14).

### Como o modelo foi testado
- **Ensaio com o 2º turno de 2022:** reproduzimos a apuração **na ordem real de chegada das urnas** e projetamos a
  cada momento. Com 2% apurado, o placar parcial errava **7 pontos**; o modelo, menos de 1.
- **Ensaio com o 1º turno de 2026:** projetamos 2026 a partir de 2022, sem ajustar nada a esses dados.
- **A auditoria do 1º turno de 2026** confirmou que os dados do TSE são coerentes (a soma bate voto a voto), o que
  é pré-condição para qualquer projeção.
- **Resultado destes ensaios, para este modelo** (erro em pontos percentuais, a cada ponto da apuração):

  | Ensaio | 2% | 3% | 5% | 10% | 20% | 50% |
  |---|---|---|---|---|---|---|
  | 2022 1º turno → 2026 1º turno | −0,45 | +0,20 | +0,29 | +0,61 | +0,78 | +0,39 |
  | 2022 1º turno → 2022 2º turno | −0,71 | −0,59 | +0,01 | +0,32 | +0,45 | +0,52 |

- Daí vem a **margem de ±0,8 ponto percentual**: o maior erro observado (0,78), arredondado para cima. É uma
  regra **fixada antes da eleição** (pré-registro), e não uma garantia de probabilidade.
- O sistema principal do projeto, que roda no computador do Eduardo, faz a média deste modelo com um segundo
  modelo ("matriz de transferência"). A média erra menos (no máximo 0,63), por isso usa ±0,7. Este caderno é o
  **sistema reserva**, independente: outra base, outro código, outra máquina.

**Regra para apontar vencedor:** só quando a margem inteira fica de um lado de 50%, isto é, quando a projeção está
fora da faixa de 49,2% a 50,8%. Fora disso, o cartão diz "empate técnico".

**Cobertura geográfica:** nos ensaios, os 24 estados só foram alcançados com cerca de **10% apurado** (17h33 em
2022). Antes disso a projeção é calculada, mas não é publicada.
""")
codigo(r"""
def projetar(tabela_ao_vivo, base, k_mun=2000.0, k_uf=10000.0):
    # tabela_ao_vivo: uma linha por município, com o que já foi apurado (Parte 9).
    # base: uma linha por município, com o 1º turno (Parte 8).
    d = tabela_ao_vivo.merge(base, on=["uf", "mun"], how="left")
    m = d[d["A1"].notna()].copy()                       # municípios com base (inclui o exterior, "zz")
    sem_base = d[d["A1"].isna()]                        # raros: municípios novos, entram só com o que já foi apurado

    m["f"] = (m["est"] / m["te"].clip(lower=1)).where(m["st"] < m["ts"], 1.0)   # passo 2
    m.loc[m["st"] == 0, "f"] = 0.0
    v1 = (m["A1"] + m["B1"]).clip(lower=1)
    s1 = m["A1"] / v1                                                            # passo 1
    m["v2"] = m["A2c"] + m["B2c"]                       # votos dos dois candidatos já apurados
    m["v1_ap"] = v1 * m["f"]                            # votos do 1º turno na parte apurada
    m["swing_votos"] = m["A2c"] - m["v2"] * s1                                   # passo 3

    total = m[["swing_votos", "v2", "v1_ap"]].sum()
    swing_pais = total["swing_votos"] / max(total["v2"], 1)
    razao_pais = total["v2"] / max(total["v1_ap"], 1)
    g = m.groupby("uf")[["swing_votos", "v2", "v1_ap"]].sum()
    swing_uf = (g["swing_votos"] + k_uf * swing_pais) / (g["v2"] + k_uf)         # passo 4, estado
    razao_uf = (g["v2"] + k_uf * razao_pais) / (g["v1_ap"] + k_uf)               # passo 5, estado
    swing_m = (m["swing_votos"] + k_mun * m["uf"].map(swing_uf)) / (m["v2"] + k_mun)   # passo 4, município
    razao_m = (m["v2"] + k_mun * m["uf"].map(razao_uf)) / (m["v1_ap"] + k_mun)         # passo 5, município

    faltam = v1 * (1 - m["f"]) * razao_m                                         # passo 6
    a_faltam = (s1 + swing_m).clip(0, 1) * faltam
    A = m["A2c"].sum() + a_faltam.sum() + sem_base["A2c"].sum()                  # passo 7
    B = m["B2c"].sum() + (faltam - a_faltam).sum() + sem_base["B2c"].sum()

    brasil = m[m["uf"] != "zz"]                         # o exterior entra na conta, mas não é um "estado"
    cobertura_uf = brasil.groupby("uf").apply(lambda x: (x["f"] * x["te"]).sum() / max(x["te"].sum(), 1),
                                              include_groups=False)
    return {"share_a": 100 * A / (A + B),
            "pct_apurado": 100 * (m["f"] * m["te"]).sum() / max(m["te"].sum(), 1),
            "estados_com_dados": int((cobertura_uf >= 0.01).sum())}


def pronta(p, minimo_pct=2.0, minimo_estados=24):
    # regra de representatividade: só publica com apuração suficiente E espalhada pelo país
    return p["pct_apurado"] >= minimo_pct and p["estados_com_dados"] >= minimo_estados

print("Modelo pronto.")
""")

# =====================================================================================================================
texto(r"""
# Parte 8 · Montando a base do 1º turno

### Os endereços do TSE
Os arquivos ficam em `https://resultados.tse.jus.br/oficial/ele2026/...`. As funções abaixo montam os endereços a
partir do código da eleição, do estado (`uf`) e do município (`mun`). Um exemplo real:
`.../ele2026/6257/dados/sp/sp71072-c0001-e006257-u.json` é o resultado para presidente (`c0001`) no município 71072,
que é a capital, São Paulo.

### Lendo os arquivos
Os arquivos JSON do TSE usam abreviações: `ts` = total de seções, `st` = seções totalizadas (apuradas), `te` =
total de eleitores, `est` = eleitores das seções totalizadas, `vap` = votos apurados do candidato. As funções
`ler_resultado` e `ler_andamento` traduzem isso para algo mais fácil de usar.

### A base
O 1º turno é baixado **uma única vez** (cerca de 5.800 arquivos, uns 7 minutos no ritmo educado) e guardado no
Drive como `base_6257.csv`. Nas próximas vezes, a célula só lê esse arquivo, em segundos.
""")
codigo(r"""
SITE = "https://resultados.tse.jus.br/oficial/ele2026"
ESTADOS = ["ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb", "pe", "pi", "pr",
           "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to", "zz"]          # "zz" = exterior

def url_resultado(eleicao, uf, mun=None):
    area = f"{uf}{str(mun).zfill(5)}" if mun else uf
    return f"{SITE}/{eleicao}/dados/{uf}/{area}-c0001-e{eleicao.zfill(6)}-u.json"

def url_andamento(eleicao, uf):
    return f"{SITE}/{eleicao}/dados/{uf}/{uf}-e{eleicao.zfill(6)}-ab.json"

def numero(x):                     # o TSE escreve números como texto ("1.234" ou "1234"); converte para inteiro
    try:
        return int(str(x).replace(".", "").replace(",", ""))
    except (TypeError, ValueError):
        return 0

def ler_resultado(j):
    votos = {}
    for cargo in j.get("carg", []):
        if cargo.get("cd") == "1":                     # cargo 1 = presidente
            for agr in cargo.get("agr", []):
                for par in agr.get("par", []):
                    for cand in par.get("cand", []):
                        votos[str(cand["n"])] = numero(cand.get("vap"))
    e, s = j.get("e", {}), j.get("s", {})
    return {"votos": votos, "te": numero(e.get("te")), "est": numero(e.get("est")),
            "ts": numero(s.get("ts")), "st": numero(s.get("st"))}

def ler_andamento(j, uf):
    linhas = []
    for a in j.get("abr", []):
        if a.get("tpabr") == "mun":                    # uma linha por município
            s, e = a.get("s", {}), a.get("e", {})
            linhas.append({"uf": uf, "mun": str(int(a["cdabr"])), "ts": numero(s.get("ts")), "st": numero(s.get("st")),
                           "te": numero(e.get("te")), "atualizado": f"{a.get('dt', '')} {a.get('ht', '')}"})
    return linhas

def montar_base(baixador, eleicao, num_a, num_b, arquivo):
    arquivo = Path(arquivo)
    if arquivo.exists():                              # já existe: só lê (sem acessar o TSE)
        return pd.read_csv(arquivo, dtype={"uf": str, "mun": str})
    municipios = []
    for url, (_, j) in baixador.baixar_varios([url_andamento(eleicao, uf) for uf in ESTADOS]).items():
        uf = url.split("/")[-2]
        municipios += [(uf, r["mun"]) for r in ler_andamento(j, uf)] if j else []
    respostas = baixador.baixar_varios([url_resultado(eleicao, uf, m) for uf, m in municipios])
    linhas = []
    for (uf, m), (_, j) in zip(municipios, respostas.values()):
        if j:
            r = ler_resultado(j)
            linhas.append({"uf": uf, "mun": m, "A1": r["votos"].get(num_a, 0), "B1": r["votos"].get(num_b, 0),
                           "eleitores1": r["te"]})
    base = pd.DataFrame(linhas)
    base.to_csv(arquivo, index=False)
    return base

baixador_base = Baixador(os.path.join(PASTA_COMPARTILHADA, f"e{ELEICAO_BASE}_base"), CONEXOES, MAX_POR_SEGUNDO)
base = montar_base(baixador_base, ELEICAO_BASE, NUM_A, NUM_B, os.path.join(PASTA_COMPARTILHADA, f"base_{ELEICAO_BASE}.csv"))
print(f"Base: {len(base):,} municípios | {NOME_A}: {base.A1.sum():,} votos | {NOME_B}: {base.B1.sum():,} votos")
""")

# =====================================================================================================================
texto(r"""
# Parte 9 · Acompanhando a apuração ao vivo

A cada ciclo, o programa:
1. baixa o resultado nacional e os **28 arquivos de andamento** (27 estados e o exterior). São poucos pedidos e
   quase sempre voltam como "não mudou";
2. descobre **quais municípios mudaram** desde o ciclo anterior;
3. baixa o resultado **só desses municípios**, com os maiores primeiro, até 900 por ciclo; o resto fica "adiado"
   (*deferred*) para o próximo.

### A regra de ouro da consistência
Os votos de um município e a quantidade de seções apuradas dele têm de vir **do mesmo arquivo, do mesmo momento**.
Se o download de um município falha, ele continua com a última versão boa e é tentado de novo. **Nunca** pode
acontecer de "seções apuradas" serem novas e os votos velhos (ou ausentes). Foi exatamente esse o bug mais grave que
os testes encontraram (Parte 14).
""")
codigo(r"""
class AoVivo:
    def __init__(self, baixador, eleicao, num_a, num_b, max_por_ciclo):
        self.b, self.eleicao, self.num_a, self.num_b = baixador, eleicao, num_a, num_b
        self.max_por_ciclo = max_por_ciclo
        self.andamento = {}          # (uf, mun) -> linha do arquivo de andamento
        self.municipios = {}         # (uf, mun) -> votos e progresso, do MESMO arquivo de resultado
        self.pendentes = set()       # falharam ou foram adiados: entram primeiro no próximo ciclo
        self.nacional = None

    def ciclo(self):
        t0 = time.time()
        fixos = [url_resultado(self.eleicao, "br")] + [url_andamento(self.eleicao, uf) for uf in ESTADOS]
        r = self.b.baixar_varios(fixos)
        if r[fixos[0]][1]:
            self.nacional = ler_resultado(r[fixos[0]][1])
        mudaram = []
        for uf in ESTADOS:
            j = r[url_andamento(self.eleicao, uf)][1]
            for linha in (ler_andamento(j, uf) if j else []):
                chave = (uf, linha["mun"])
                antes = self.andamento.get(chave)
                self.andamento[chave] = linha
                novo = antes is None or (antes["st"], antes["atualizado"]) != (linha["st"], linha["atualizado"])
                if linha["st"] > 0 and (novo or chave not in self.municipios):
                    mudaram.append(chave)
        # pendentes primeiro; depois os de maior eleitorado; até o limite por ciclo
        fila = list(dict.fromkeys(sorted(self.pendentes) +
                                  sorted(mudaram, key=lambda k: -self.andamento.get(k, {}).get("te", 0))))
        agora, adiados = fila[:self.max_por_ciclo], fila[self.max_por_ciclo:]
        respostas = self.b.baixar_varios([url_resultado(self.eleicao, uf, mun) for uf, mun in agora])
        falhas, self.pendentes = 0, set(adiados)
        codigos = [r[u][0] for u in fixos]
        for chave, (codigo, j) in zip(agora, respostas.values()):
            codigos.append(codigo)
            if j:
                x = ler_resultado(j)
                self.municipios[chave] = {"A2c": x["votos"].get(self.num_a, 0), "B2c": x["votos"].get(self.num_b, 0),
                                          "st": x["st"], "ts": x["ts"], "est": x["est"], "te": x["te"]}
            else:
                falhas += 1
                self.pendentes.add(chave)            # mantém a última versão boa; tenta de novo
        falhas_fixos = sum(1 for u in fixos if r[u][0] not in (200, 304))
        pedidos = len(fixos) + len(agora)
        return {"hora": datetime.now(BRASILIA).strftime("%H:%M:%S"), "baixados": len(agora), "adiados": len(adiados),
                "taxa_falhas": round((falhas + falhas_fixos) / max(pedidos, 1), 3),
                "codigos": {str(c): codigos.count(c) for c in sorted(set(codigos), key=str)},
                "segundos": round(time.time() - t0, 1)}

    def tabela(self):
        linhas = []
        for (uf, mun), a in self.andamento.items():
            v = self.municipios.get((uf, mun))
            if v:
                linhas.append({"uf": uf, "mun": mun, **v})
            else:                                    # nunca lido: conta como ainda não apurado
                linhas.append({"uf": uf, "mun": mun, "A2c": 0, "B2c": 0, "st": 0, "ts": a["ts"], "est": 0, "te": a["te"]})
        return pd.DataFrame(linhas)

print("Classe AoVivo pronta.")
""")

# =====================================================================================================================
texto(r"""
# Parte 10 · Ensaio com o 1º turno

Com `ELEICAO = "6257"`, os arquivos do 1º turno já estão completos. Projetar o 1º turno a partir dele mesmo tem de
dar **exatamente o resultado oficial**: 51,0115% para Flávio Bolsonaro entre os dois. É um teste de que todas as
peças estão encaixadas.

No primeiro ciclo, o programa baixa os 900 maiores municípios (cerca de 71% do eleitorado) e adia o resto. Mesmo
assim, a projeção já deve dar 51,01%, porque o modelo estima os que faltam.

> Este ensaio faz cerca de 930 pedidos ao TSE. Não precisa repeti-lo muitas vezes.
""")
codigo(r"""
ao_vivo = AoVivo(Baixador(os.path.join(PASTA, f"e{ELEICAO}"), CONEXOES, MAX_POR_SEGUNDO), ELEICAO, NUM_A, NUM_B,
                 MAX_MUNICIPIOS_POR_CICLO)
c = ao_vivo.ciclo()
print("ciclo:", c)
p = projetar(ao_vivo.tabela(), base)
print(f"projeção {NOME_A}: {p['share_a']:.4f}% | apurado {p['pct_apurado']:.1f}% | "
      f"estados com dados: {p['estados_com_dados']} | pronta para publicar: {pronta(p)}")
""")

# =====================================================================================================================
texto(r"""
# Parte 11 · O cartão para a mídia

Esta parte vem antes do laço porque o laço usa a função `fazer_cartao`. A primeira célula só **define** a função;
o cartão é desenhado quando o laço a chama, ou quando você roda a célula seguinte.

Uma imagem vertical de 1080×1350 pixels (o formato que funciona no LinkedIn, Instagram, X e WhatsApp), desenhada com
`matplotlib`. Cuidados de comunicação embutidos no código:
- **cores neutras**, sem cores partidárias;
- **"NÃO é resultado oficial"** sempre visível;
- **vencedor só aparece se a margem permitir**; caso contrário, "empate técnico";
- **marca d'água** "SIMULAÇÃO" nos testes e "BACKUP · NÃO PUBLICAR" nos ajudantes.
""")
codigo(r"""
import matplotlib
import matplotlib.pyplot as plt

def fazer_cartao(csv_proj, png, meia_margem=MEIA_MARGEM, marca=MARCA_DAGUA, data_rotulo="25 de outubro de 2026"):
    d = pd.read_csv(csv_proj)
    apurando = d[d["pct_electorate_counted"] > 0]             # linhas antes do 1º resultado puxariam o gráfico para 0%
    d = apurando.reset_index(drop=True) if len(apurando) else d
    d["ready"] = d["ready"].astype(str).str.lower().isin(["true", "1"])
    prontos = d[d["ready"]]
    ultima = (prontos if len(prontos) else d).iloc[-1]
    a = float(ultima["projection_a"]) if len(prontos) else float("nan")
    b = 100 - a
    if not len(prontos):
        situacao, cor = "Aguardando cobertura geográfica suficiente", "#6b6f76"
    elif a - meia_margem > 50:
        situacao, cor = f"Vencedor projetado: {NOME_A}", "#1f6f8b"
    elif a + meia_margem < 50:
        situacao, cor = f"Vencedor projetado: {NOME_B}", "#b5523a"
    else:
        situacao, cor = "Empate técnico: ainda sem vencedor projetado", "#8a6d1d"
    if marca:
        situacao = f"{marca} · " + situacao
    TINTA, CINZA, GRADE, FUNDO, CA, CB = "#15171a", "#6b6f76", "#e4e6ea", "#fbfbfc", "#1f6f8b", "#b5523a"
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=FUNDO)
    def t(x, y, s, **k):
        fig.text(x, y, s, color=k.pop("color", TINTA), **k)
    virgula = lambda v, casas=1: f"{v:.{casas}f}".replace(".", ",")
    t(0.07, 0.945, "PROJEÇÃO DO 2º TURNO PRESIDENCIAL", size=15, weight="bold", color=CINZA)
    t(0.07, 0.918, f"{data_rotulo}  ·  atualizado às {str(ultima['t_brt'])[:5].replace(':', 'h')}", size=15, color=CINZA)
    t(0.07, 0.885, f"{virgula(float(ultima['pct_electorate_counted']))}% do eleitorado apurado  ·  "
                   f"{int(ultima['ufs_with_1pct'])} de 27 estados com dados", size=15, color=CINZA)
    if len(prontos):
        t(0.07, 0.80, NOME_A, size=24, color=CA, weight="bold")
        t(0.93, 0.80, NOME_B, size=24, color=CB, weight="bold", ha="right")
        t(0.07, 0.715, virgula(a) + "%", size=78, color=CA, weight="bold")
        t(0.93, 0.715, virgula(b) + "%", size=78, color=CB, weight="bold", ha="right")
        barra = fig.add_axes([0.07, 0.675, 0.86, 0.022])
        barra.barh([0], [a], color=CA, height=1); barra.barh([0], [b], left=[a], color=CB, height=1)
        barra.axvline(50, color=FUNDO, lw=3); barra.set_xlim(0, 100); barra.axis("off")
        t(0.5, 0.645, f"margem estimada ±{virgula(meia_margem)} ponto percentual", size=14, color=CINZA, ha="center")
    else:
        t(0.07, 0.74, "Projeção ainda não publicada", size=36, weight="bold")
    fig.text(0.5, 0.597, situacao, ha="center", va="center", size=18, weight="bold", color=cor,
             bbox=dict(boxstyle="round,pad=0.7,rounding_size=0.9", fc=matplotlib.colors.to_rgba(cor, 0.10), ec="none"))
    ax = fig.add_axes([0.11, 0.17, 0.82, 0.36], facecolor=FUNDO)
    horas = pd.to_datetime("2000-01-01 " + d["t_brt"].astype(str))
    if len(prontos):
        hp, pa = horas[d["ready"]], prontos["projection_a"].astype(float)
        ax.fill_between(hp, pa - meia_margem, pa + meia_margem, color=CA, alpha=0.12, lw=0)
        ax.plot(hp, pa, color=CA, lw=3, label=f"projeção ({NOME_A})")
        if hp.nunique() < 2:
            ax.plot(hp, pa, "o", color=CA, ms=9)
            ax.set_xlim(hp.min() - pd.Timedelta(minutes=10), hp.max() + pd.Timedelta(minutes=10))
    ax.plot(horas, d["raw_a"].astype(float), color=CINZA, lw=1.5, ls=(0, (3, 3)), label="placar parcial bruto")
    ax.axhline(50, color=TINTA, lw=1, alpha=0.4)
    ax.set_ylabel(f"% de {NOME_A} entre os dois", color=CINZA, size=13)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",").rstrip("0").rstrip(",")))
    ax.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator(minticks=3, maxticks=8))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Hh%M"))
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", color=GRADE); ax.tick_params(colors=CINZA, labelsize=12)
    ax.legend(frameon=False, fontsize=12, labelcolor=CINZA, loc="upper right")
    t(0.07, 0.555, "Evolução ao longo da apuração", size=16, weight="bold")
    t(0.07, 0.095, "Projeção estatística independente, NÃO é resultado oficial. Fonte dos dados: TSE.", size=13, weight="bold")
    t(0.07, 0.07, "Modelo: comparação de cada município com o próprio 1º turno, a partir das urnas já apuradas.", size=12, color=CINZA)
    t(0.07, 0.035, "Eduardo Wizentier  ·  desenvolvido com Claude Opus 5.5 (Anthropic)", size=12, color=CINZA)
    if marca:
        fig.text(0.5, 0.42, marca, size=110 if len(marca) <= 10 else 50, color="#d0342c", alpha=0.13,
                 ha="center", va="center", rotation=28, weight="bold")
    fig.savefig(png, dpi=100, facecolor=FUNDO)
    plt.close(fig)
    return png

print("Função fazer_cartao pronta.")
""")
codigo(r"""
# Mostra o cartão mais recente na tela (rode quando quiser, depois de o laço ter gravado projeções)
from IPython.display import Image, display
arquivo_proj = os.path.join(PASTA, f"projections_e{ELEICAO}.csv")
if os.path.exists(arquivo_proj):
    display(Image(filename=fazer_cartao(arquivo_proj, os.path.join(PASTA, f"card_e{ELEICAO}.png"))))
else:
    print("Ainda não há projeções gravadas. Rode o laço da Parte 12 primeiro.")
""")

# =====================================================================================================================
texto(r"""
# Parte 12 · O laço da noite da eleição

Este é o coração do sistema: um laço `while True` (repita para sempre) que, a cada `INTERVALO_S` segundos, faz um
ciclo, projeta, grava uma linha no arquivo de projeções e, a cada `CARTAO_A_CADA_MIN` minutos, salva um cartão.

**Recuo automático:** se mais de 20% dos pedidos falharem, o próximo ciclo espera mais (60 s, depois 120 s, até
300 s) e o programa **não gera cartão** naquele ciclo. Quando volta ao normal, o ritmo também volta.

**Para parar,** clique no botão ■ ao lado da célula. O aviso `KeyboardInterrupt` que aparece em seguida é normal.

**No dia 25 de outubro:** mude `ELEICAO` para `"6258"` na Parte 2, rode as células de novo até aqui e deixe esta
rodando a partir das 16h50. Ela para sozinha às 21h.
""")
codigo(r"""
import csv
arquivo_proj = os.path.join(PASTA, f"projections_e{ELEICAO}.csv")
pasta_cartoes = os.path.join(PASTA, "cards")
os.makedirs(pasta_cartoes, exist_ok=True)
ao_vivo = AoVivo(Baixador(os.path.join(PASTA, f"e{ELEICAO}"), CONEXOES, MAX_POR_SEGUNDO), ELEICAO, NUM_A, NUM_B,
                 MAX_MUNICIPIOS_POR_CICLO)
espera, ultimo_cartao = INTERVALO_S, 0.0
novo = not os.path.exists(arquivo_proj)
with open(arquivo_proj, "a", newline="") as f:
    w = csv.writer(f)
    if novo:
        w.writerow(["t_brt", "pct_electorate_counted", "ufs_with_1pct", "raw_a", "projection_a", "ready"])
    while True:
        t0 = time.time()
        try:
            c = ao_vivo.ciclo()
            nac = ao_vivo.nacional or {"votos": {}}
            va, vb = nac["votos"].get(NUM_A, 0), nac["votos"].get(NUM_B, 0)
            bruto = 100 * va / max(va + vb, 1)                       # o placar "cru" do TSE, sem modelo
            p = projetar(ao_vivo.tabela(), base)
            ok = pronta(p)
            w.writerow([c["hora"], round(p["pct_apurado"], 3), p["estados_com_dados"], round(bruto, 3),
                        round(p["share_a"], 3), ok])
            f.flush()
            situacao = (f"PROJEÇÃO {NOME_A} {p['share_a']:.2f}% / {NOME_B} {100 - p['share_a']:.2f}%" if ok
                        else "aguardando cobertura geográfica")
            print(f"{c['hora']} | apurado {p['pct_apurado']:5.2f}% | estados {p['estados_com_dados']:2d} | "
                  f"placar bruto {bruto:5.2f}% | {situacao} | ciclo {c['segundos']}s"
                  + (f" | {c['adiados']} adiados" if c["adiados"] else ""), flush=True)
            if c["taxa_falhas"] > 0.2:                               # recuo automático
                espera = min(max(espera * 2, 60), 300)
                ao_vivo.b.conexoes = max(4, ao_vivo.b.conexoes // 2)
                print(f"   recuo: {c['taxa_falhas']:.0%} dos pedidos falharam {c['codigos']} -> próximo ciclo em {espera}s",
                      flush=True)
            else:
                espera, ao_vivo.b.conexoes = INTERVALO_S, CONEXOES
            if ok and c["taxa_falhas"] <= 0.2 and time.time() - ultimo_cartao >= CARTAO_A_CADA_MIN * 60:
                nome = os.path.join(pasta_cartoes, f"card_e{ELEICAO}_{c['hora'][:5].replace(':', '')}.png")
                fazer_cartao(arquivo_proj, nome)
                Path(os.path.join(pasta_cartoes, f"card_e{ELEICAO}_latest.png")).write_bytes(Path(nome).read_bytes())
                ultimo_cartao = time.time()
                print("   cartão salvo:", os.path.basename(nome), flush=True)
        except Exception as erro:
            espera = min(max(espera * 2, 60), 300)
            print(f"erro no ciclo, continuando em {espera}s:", type(erro).__name__, erro, flush=True)
        if datetime.now(BRASILIA).strftime("%H:%M") >= HORA_PARAR:
            break
        time.sleep(max(1, espera - (time.time() - t0)))
""")

# =====================================================================================================================
texto(r"""
# Parte 13 · Diagnóstico

Lê o registro de pedidos (`fetch_log.jsonl`) e conta os códigos de resposta dos últimos `N_MIN` minutos.
É assim que descobrimos os 4.246 erros 429 nos testes.
""")
codigo(r"""
import collections
N_MIN = 60
desde = (datetime.now(timezone.utc) - timedelta(minutes=N_MIN)).isoformat()
contagem, ruins = collections.Counter(), 0
registro = os.path.join(PASTA, f"e{ELEICAO}", "fetch_log.jsonl")
if os.path.exists(registro):
    for linha in open(registro, encoding="utf-8", errors="replace"):
        try:
            e = json.loads(linha)
        except json.JSONDecodeError:
            ruins += 1
            continue
        if e.get("t_utc", "") >= desde:
            contagem[(e.get("status"), e.get("error", "")[:60])] += 1
for (codigo_http, erro), n in contagem.most_common():
    print(f"{n:7d}  código {codigo_http}  {erro}")
print(f"(linhas danificadas ignoradas: {ruins})")
""")

# =====================================================================================================================
texto(r"""
# Parte 14 · O que os testes nos ensinaram

Cada um destes problemas foi encontrado **rodando o programa de verdade**, e não lendo o código. Essa é talvez a
lição mais importante de engenharia de software: **teste com dados reais, e desconfie de resultados bons demais
ou estranhos.**

| # | Sintoma | Causa | Correção |
|---|---|---|---|
| 1 | Projeção de **45,92%** em vez de 51,01% | Downloads que falharam: o município ficava "apurado" mas sem votos, e contava como zero votos | Votos e progresso vêm do mesmo arquivo; quem falhou conta como "não apurado" e é tentado de novo |
| 2 | Muitas falhas seguidas | O TSE respondeu **429** (pedidos demais) a rajadas de 32 downloads | Ritmo máximo, pausa no 429 e prioridade aos grandes |
| 3 | Projeção "parada" em 51,03% até o último município chegar | Os votos do **exterior** ainda não lidos contavam como zero | O exterior entra no modelo como mais um "estado" |
| 4 | "28 de 27 estados" no cartão | O exterior passou a ser contado como estado | O exterior conta na projeção, mas não na contagem de estados |
| 5 | Erro ao ler o registro | Linhas misturadas: vários threads escrevendo no mesmo arquivo ao mesmo tempo | Uma **trava** (`threading.Lock`) para escrever; leitura que pula linhas danificadas |

Repare no bug 1: um erro de **coleta de dados** causou um desvio de 5 pontos, **dez vezes maior** que o erro do
modelo estatístico (±0,5). Engenharia de dados e estatística têm o mesmo peso.
""")

# =====================================================================================================================
texto(r"""
# Parte 15 · Exercícios

Bons para praticar. Nenhum precisa de acesso ao TSE, exceto o 6.

1. **Hash:** na Parte 5, troque o texto `b` por outra frase e conte de novo quantos caracteres do hash coincidem.
   Por que o número fica sempre perto de 4? (Dica: são 16 símbolos possíveis em cada uma das 64 posições.)
2. **Ritmo:** na demonstração da Parte 4, mude o limite para 5 pedidos por segundo. Quanto tempo devem levar os 30
   pedidos? Confira.
3. **Tabelas com pandas:** usando a variável `base`, descubra em qual estado Lula teve a maior porcentagem no 1º
   turno. (Dica: `base.groupby("uf")[["A1", "B1"]].sum()` e depois uma divisão.)
4. **Gráfico:** faça um gráfico de barras com a porcentagem de Flávio por estado no 1º turno.
5. **O efeito do encolhimento:** na função `projetar`, mude `k_mun` para 0 e para 100000. O que acontece com a
   projeção logo no começo da apuração, quando há poucas urnas? Por que um valor intermediário é melhor?
6. **Desafio:** depois de 25/10, compare as projeções gravadas no arquivo `projections_e6258.csv` com o resultado
   oficial final. Qual foi o erro com 2%, 5% e 10% apurado? Ficou dentro de ±0,8?
""")

nb = {"cells": celulas, "metadata": {"colab": {"provenance": []}, "kernelspec": {"name": "python3",
      "display_name": "Python 3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}
saida = AQUI / "aprenda_apuracao_ao_vivo.ipynb"
saida.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("gerado:", saida, len(celulas), "células")
