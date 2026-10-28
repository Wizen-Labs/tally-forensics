# Entenda-me: o projeto tally-forensics, explicado passo a passo

> **Autor:** Eduardo Wizentier ([@Wizen-Labs](https://github.com/Wizen-Labs)).
>
> Guia didático do projeto. Ele explica **o que** foi construído, **por quê** e **como ler** os resultados, sem
> exigir que se leia o código. Os números citados estão em `FINDINGS.md`, onde cada um aponta para o relatório que
> o gerou. Este guia está em português; o restante do repositório está em inglês.

---

## 1. O projeto em uma frase

Usamos **apenas dados públicos do TSE** para fazer uma **auditoria estatística**: verificar se a apuração do 1º
turno de 2026 tem padrões que sugiram interferência, olhando o *lugar* e o *horário* em que cada urna foi contada.
<!-- phase2:start -->

Há também uma Parte B, a projeção ao vivo do 2º turno a partir de 2% a 5% das urnas. Ela ficou no laboratório
privado até depois da eleição, com o hash publicado, e foi revelada em 28/10/2026.
<!-- phase2:end -->

---

## 2. De onde veio a ideia

1. **A auditoria** nasceu de um fato: em 04/10/2026, entre cerca de 19h00 e 20h08, a divulgação nacional
   para presidente **travou** em 64% e voltou já em 85%. O TSE atribuiu o problema a congestionamento. A pergunta:
   o que aconteceu nessa janela deixou alguma marca nos votos? E existem padrões por região ou por horário que não
   se expliquem por causas normais? **A ideia da auditoria é do autor, Eduardo Wizentier:** examinar os desvios com dois filtros, um
   geográfico e outro de horário de transmissão. A implementação estatística (comparar cada seção com as vizinhas
   do mesmo prédio, teste de permutação, calibração) foi desenvolvida com o Claude Opus 5.5.
2. Todos os dados são públicos, do TSE. A análise e o código foram desenvolvidos com o Claude Opus 5.5, da
   Anthropic.
<!-- phase2:start -->
3. **A projeção em tempo real (Parte B):**
   - um componente dela, o **modelo de swing municipal**, foi inspirado no trabalho de Rodrigo Mahlmeister,
     divulgado pela NeoFeed;
   - nenhum código dele foi usado; a implementação é independente.
<!-- phase2:end -->

---

## 3. A matéria-prima: o boletim de urna

Quando a votação termina, **cada urna imprime e transmite um boletim (BU)**: quantos votos cada candidato teve
naquela seção. O TSE publica todos esses boletins em arquivos abertos (`bweb_1t_<UF>_....zip`), um por estado.

Cada linha traz, entre outras coisas:

| Informação | Exemplo | Para que usamos |
|---|---|---|
| Estado, município, zona, seção, local de votação | SP, 71072, zona 389, seção 524, local 1775 | Saber **onde** é a urna e quem são as "vizinhas" |
| Votos por candidato, brancos, nulos | 22 = 150, 13 = 120 ... | O resultado da seção |
| Aptos, comparecimento, abstenção | 312, 255, 57 | Checagens e participação |
| **Horários**: abertura, encerramento, emissão do BU, **recebimento no TSE** | 18:31:08 | Saber **quando** a urna entrou na contagem |

Dois detalhes técnicos que descobrimos e que a ferramenta trata sozinha:

- **Hash:** cada arquivo do TSE vem com um "selo" SHA-512. A ferramenta confere esse selo; se um único byte
  estiver diferente, ela recusa o arquivo.
- **Fuso horário:** os horários da urna estão na **hora local** (em Roraima a urna abre às 7h), mas o recebimento no
  TSE está na **hora de Brasília**. A ferramenta descobre o fuso de cada município olhando a que horas as urnas
  abriram e converte tudo para Brasília.

---

## 4. A auditoria estatística, passo a passo

### Passo 1: baixar e conferir
`python -m tally fetch` baixa os 28 arquivos (27 estados e o exterior), confere o hash e registra tudo num
"manifesto". **Nada é sobrescrito**: se um arquivo mudar no TSE, a ferramenta para e avisa.

### Passo 2: montar a tabela de seções
`python -m tally build` lê os arquivos (que são enormes; o de SP tem 1,4 GB) e monta **uma linha por seção** com os
votos para presidente e os horários já convertidos para Brasília. São cerca de 500 mil seções.

### Passo 3: checagens que não dependem de estatística
São verificações do tipo **certo ou errado**:

| Checagem | Pergunta |
|---|---|
| I1 | A soma dos votos da seção bate com o número de pessoas que votaram? |
| I2 | Aptos = compareceram + faltaram? |
| I3 | Alguma seção teve mais votantes do que eleitores? |
| I4 | Alguma seção aparece duas vezes? |
| I5 | Alguma urna física aparece em duas seções? |
| I6 | Os horários estão em ordem (abriu, fechou, imprimiu, transmitiu)? |
| I7 | Algum boletim chegou ao TSE antes das 17h? |
| **R** | **A soma de todos os boletins dá exatamente o total oficial divulgado?** |

**Resultado em 2026:** a soma dos 499.206 boletins bate com o total oficial **voto a voto** (Flávio 56.104.503,
Lula 53.879.538). As 60 falhas de horário (I6) são um defeito da própria ferramenta: em alguns municípios do MT,
parte das urnas usa o relógio de Brasília e parte a hora local, e a ferramenta atribui um único fuso por
município. Não são um problema dos dados.

### Passo 4: a ideia central, comparar cada seção com as vizinhas do mesmo prédio
Este é o coração da auditoria. Uma analogia ajuda:

> Imagine uma escola com 6 salas de votação. Os eleitores das 6 salas moram no mesmo bairro, então elas votam de
> forma **parecida**. Se a sala 3 der 10 pontos a mais para um candidato do que as outras 5, isso chama atenção.

Para cada seção calculamos o **resíduo**:

```
resíduo = (% do candidato nesta seção) − (% do candidato nas OUTRAS seções do mesmo local de votação)
```

Por que isso é poderoso:
- não precisa de modelo, de pesquisa nem da eleição anterior, então **não há nada para ajustar**;
- a geografia, a renda e a política local são as mesmas para todas as salas do prédio, e por isso se anulam.

### Passo 5: o filtro de horário e o teste de permutação
Pergunta: **as seções que chegaram durante o travamento (19h00–20h08) discordam mais das vizinhas do que as que
chegaram em outros horários?**

Como saber se uma diferença é real ou acaso? Com o **teste de permutação**:

1. Calculamos a diferença média real: seções "dentro da janela" contra suas vizinhas "fora da janela".
2. Dentro de cada prédio, **embaralhamos as etiquetas** "dentro" e "fora" ao acaso, mantendo quantas seções de cada
   tipo o prédio tem, e recalculamos. Repetimos 2.000 vezes.
3. Isso mostra o tamanho de diferença que o **puro acaso** produz.
4. O **p-valor** é a fração dos embaralhamentos que deu uma diferença tão grande quanto a real.
   - p = 0,40 significa que o acaso produz algo assim 40% das vezes: nada de anormal.
   - p < 0,01 significa que o acaso quase nunca produz isso: vale investigar.

### Passo 6: janelas placebo, um "controle negativo"
Repetimos o mesmo teste em janelas **onde nada aconteceu** (17h52–19h00 e 20h08–21h16) e na **mesma janela de 2022**,
quando não houve travamento. Se o teste "acusar" nesses casos, quem está com defeito é o teste, não a eleição.

### Passo 7: a calibração em 2022 achou um defeito, e isso foi bom
Antes de olhar 2026, rodamos tudo em 2022. O teste **acusou** numa janela placebo (p = 0,001). Investigando,
achamos causas inocentes:

- **Fila:** seções com fila fecham mais tarde e transmitem mais tarde, e quem fica na fila vota um pouco diferente.
- **Seções mais novas:** num mesmo prédio, as seções de número mais alto costumam ter eleitores mais jovens.

**Correção:** o teste principal passou a descontar essas diferenças (horário de fechamento, posição da seção no
prédio, tamanho). Isso é legítimo porque tudo isso é definido **na urna, antes da transmissão**, e portanto não pode
esconder uma manipulação feita na transmissão. Depois do ajuste, nenhum teste de 2022 acusou nada, e um teste com
dados inventados mostrou que ele **ainda detecta** uma fraude de 5% plantada de propósito.

### Passo 8: pré-registro e congelamento
Antes de olhar 2026, escrevemos as hipóteses e a regra de decisão (`METHODOLOGY.md`) e **congelamos**:
registramos o hash dos arquivos de método. Isso impede ajustar o teste depois de ver o resultado, que é um erro
comum e grave em análises desse tipo. A regra exigia, ao mesmo tempo:

1. p < 0,01 na janela do travamento;
2. o mesmo sinal ao mover a janela 15 minutos para os lados;
3. nada nas janelas placebo;
4. nada na mesma janela de 2022.

### Passo 9: resultados de 2026
- **Teste principal: nada de anormal** (diferença de −0,085 ponto, p = 0,40, em 7.687 prédios).
- **Fato novo:** pelos carimbos do próprio TSE, **nenhum boletim foi registrado como recebido, em nenhum estado,
  de 19h31m50s a 19h59m22s**, uma pausa de 27,5 minutos. Em 2022, no mesmo horário, chegavam cerca de 3.400 por
  minuto.
- As seções que entraram logo depois da pausa **também não diferem** das vizinhas. A pausa foi operacional e não
  deixou marca nos votos.
- Em 2022 a "virada" Lula × Bolsonaro aconteceu às 20h, **na mesma janela**, sem travamento nenhum. Uma curva que
  muda de direção nesse horário é efeito normal da ordem de chegada das regiões.

### O que a auditoria NÃO consegue ver
Se a **própria urna** alterasse votos de forma igual em todas as seções, o boletim já sairia alterado e as vizinhas
continuariam parecidas. Nenhuma estatística por seção detecta isso. Essa camada é coberta por outros mecanismos
(inspeção de código, testes públicos, votação paralela), não por este projeto.

---

## 5. Dados ao vivo e o coletor

### O que o TSE publica ao vivo
A questão foi levantada pelo autor e foi decisiva. Verificamos nos arquivos do próprio TSE:

| O que sai | Quando |
|---|---|
| Votos **por município** e quantas seções de cada município já entraram | ~2 minutos depois da última urna do município |
| Lista e arquivos **por seção** | **horas depois** (a partir das 20h30, em lotes) |

Ou seja, ao vivo temos **totais por município**, não os votos de cada seção.

### O coletor ao vivo
`python -m tally live --election 6258 --interval 60`

A cada minuto:
1. pergunta ao TSE o que mudou, baixando só o que mudou;
2. guarda **cada versão** de cada arquivo, identificada pelo hash, sem nunca apagar;
3. com isso, depois dá para "voltar no tempo" e ver o que se sabia às 19h05, por exemplo. Foi exatamente isso que
   faltou para analisar o travamento do 1º turno.

Testado com o 1º turno: a soma dos 5.757 arquivos municipais bate **voto a voto** com o total oficial e com os
boletins de cada município.

---

<!-- phase2:start -->
## 5b. Parte B: a projeção ao vivo, passo a passo (fase 2)

### Passo 1: o problema
As primeiras urnas que chegam **não são uma amostra justa**. No 1º turno, com 2% apurado, Flávio aparecia com
50,6%, mas terminou com 47,0%: o Paraná chega cedo e pesava 26% das primeiras urnas. **Extrapolar o parcial engana.**

### Passo 2: a ideia, usar o 1º turno como régua
Cada seção já votou três semanas antes. Sabemos quantos votos ela deu a Flávio, Lula, outros, brancos e nulos e
quantos faltaram. O 2º turno de cada seção é estimado **a partir do 1º turno dela mesma**.

### Passo 3: a matriz de transferência ("para onde vai cada grupo")
Exemplo com números redondos:

| Grupo no 1º turno | Vai para A no 2º | Vai para B no 2º |
|---|---|---|
| Eleitor de A | 97% | 1% |
| Eleitor de B | 1% | 97% |
| Eleitor dos outros (Cury, Caiado, Zema...) | ? | ? |
| Branco/nulo | ? | ? |
| Abstenção | ? | ? |

As interrogações são estimadas **ao vivo**, comparando as seções já apuradas com o 1º turno delas. Uma seção com
muitos eleitores de Caiado que dá mais votos a A do que seu 1º turno previa ensina para onde foi o eleitor de
Caiado.

As estimativas são feitas **em camadas**: Brasil → região → estado. Um estado com poucas urnas apuradas "pega
emprestado" do nível acima.

### Passo 4: o backtest, ensaiar com uma eleição que já aconteceu
Reproduzimos o 2º turno de 2022 **na ordem real de chegada** das urnas e medimos o erro em cada momento:

| Urnas apuradas | Parcial bruto | Nosso modelo (com votos por seção) |
|---|---|---|
| 2% | erro de 7 pontos | erro de 0,08 ponto |
| 5% | erro de 4 pontos | erro de 0,09 ponto |

### Passo 5: o limite honesto
Testamos vários métodos usando só totais por município, inclusive um modelo de "swing por município":

- com votos por seção, o erro é de cerca de **0,1 ponto**;
- com totais por município, cerca de **0,5 ponto** na fatia de cada candidato, ou seja, cerca de 1 ponto na
  diferença entre eles, com 2–5% apurado.

**Tradução prática:** no dia 25 o modelo dará uma boa estimativa do percentual. Mas só poderá apontar o vencedor
com segurança se a diferença for claramente maior que 1 ponto. O próprio resultado do Rodrigo no 1º turno (0,02
em Flávio, 0,34 em Lula) cabe nessa faixa.

Uma armadilha que evitamos: um ajuste que parecia ótimo em 2022 piorou em 2026. Por isso testamos **fora da
amostra** (em dados que o modelo nunca viu) antes de confiar.

<!-- phase2:end -->

---

## 6. Mapa do projeto (o que é cada arquivo)

| Caminho | O que é |
|---|---|
| `entendaMe.md` | Este guia |
| `README.md` | Apresentação curta e comandos (em inglês) |
| `METHODOLOGY.md` | O método da auditoria e o **pré-registro congelado** |
| `FINDINGS.md` | **Todos os resultados**, cada um com o relatório de origem, incluindo erros e correções |
| `CHANGELOG.md` | O que mudou em cada versão |
| `CLAUDE.md` | Memória do projeto para o Claude: regras, estado atual e próximos passos |
| `config/sources.json` | Endereços dos arquivos do TSE (dados, não código) |
| `config/analysis.json` | Parâmetros congelados da auditoria |
| `tally/fetch.py` | Baixa e confere o hash |
| `tally/load.py` | Lê os boletins e converte os fusos |
| `tally/integrity.py` | Checagens certo/errado (I1–I7, R) |
| `tally/residuals.py` | Comparação de cada seção com as vizinhas do prédio |
| `tally/temporal.py` | Curva de chegada e teste de permutação |
| `tally/geo.py` | Resumos por estado e município |
| `tally/analyze.py` | Roda a auditoria completa e gera o relatório |
| `tally/project.py` | Modelos de projeção (por seção, por município, swing) | <!-- phase2 -->
| `tally/backtest.py` | Ensaios com eleições passadas | <!-- phase2 -->
| `tally/live.py` | Coletor ao vivo |
| `exploratory/` | Análises exploratórias, fora do pré-registro: a pausa de 27,5 min, a cobertura inicial, o que o TSE publica, a conferência do coletor |
| `tests/` | Testes automáticos, muitos com "eleições inventadas" cuja resposta certa conhecemos |
| `reports/` | Relatórios gerados (tabelas, gráficos) |
| `data/` | Dados baixados (não versionados; são reconstruídos pelo manifesto) |

---

## 7. Comandos principais

```bash
.venv\Scripts\python -m pytest -q                                  # roda os testes
.venv\Scripts\python -m tally all --year 2026 --all-ufs           # auditoria completa de 2026 (já feita)
.venv\Scripts\python -m tally backtest --year 2022                # ensaio da projeção no 2º turno de 2022 <!-- phase2 -->
.venv\Scripts\python -m tally live --election 6258 --interval 60  # coletor ao vivo do 2º turno
```

---

## 8. Como ler um relatório da auditoria (`reports/2026_t1_.../`)

1. **`summary.md`:** comece por aqui. Mostra as checagens certo/errado e a tabela de testes. O que importa é a
   linha `primary: freeze window | margin_resid_adj`.
2. **`arrival_curve.png`:** em cima, quantas urnas chegaram a cada 10 minutos (o "buraco" perto das 19h40 é a
   pausa); embaixo, como estaria o placar se fosse divulgado na ordem de chegada.
3. **`heatmap_uf_by_time.png`:** estados nas linhas e horário nas colunas. Vermelho e azul mostram seções
   discordando das vizinhas; tons fracos e espalhados são normais.
4. **`fingerprint.png`:** "impressão digital" da eleição (participação × votação). Manchas estranhas, como um
   acúmulo em 100% de participação e 100% de votos, seriam o alerta clássico.

---

## 9. Glossário

| Termo | Significado simples |
|---|---|
| **p.p. (ponto percentual)** | Diferença entre porcentagens. De 47% para 48% = 1 p.p. |
| **Resíduo** | Quanto uma seção se afasta das vizinhas do mesmo prédio |
| **p-valor** | Com que frequência o puro acaso produziria um resultado assim. Pequeno (< 0,01) = vale investigar |
| **Teste de permutação** | Embaralhar etiquetas milhares de vezes para ver o que o acaso faz |
| **Placebo** | Testar onde sabemos que nada aconteceu, para conferir se o teste não "vê fantasmas" |
| **Confundidor** | Causa inocente que imita um efeito (ex.: fila) |
| **Pré-registro** | Escrever as regras antes de ver os dados, para não ajustar depois |
| **Hash** | "Impressão digital" de um arquivo; muda se um único byte mudar |
| **Backtest** | Ensaio do modelo numa eleição passada, na ordem real dos fatos | <!-- phase2 -->
| **Fora da amostra** | Testar em dados que não foram usados para construir o modelo |
| **Matriz de transferência** | Tabela de "para onde foi" cada grupo de eleitores do 1º para o 2º turno | <!-- phase2 -->
| **Regressão ecológica** | Deduzir comportamento de grupos a partir de totais (não vemos eleitores, só somas) | <!-- phase2 -->
| **Swing** | Variação de um candidato entre duas eleições no mesmo lugar | <!-- phase2 -->
| **Prior** | Palpite inicial que os dados corrigem; útil quando há pouca informação | <!-- phase2 -->
| **Intervalo de 90%** | Faixa onde o resultado deve cair 9 em cada 10 vezes | <!-- phase2 -->

---

## 10. O pré-registro do 2º turno (`PREREGISTRATION_ROUND2.md`)

São as regras escritas **antes** do dia 25, para que ninguém (nem nós) possa ajustar nada depois de ver o resultado.

<!-- phase2:start -->
**Projeção ao vivo:**
- **Estimativa:** a média de dois modelos municipais (transferência e swing), nenhum com parâmetro "ajustado à
  mão".
- **Quando começa:** nada é mostrado antes de 2% das urnas apuradas.
- **Margem:** ±0,7 ponto, o pior erro visto nos dois ensaios, arredondado para cima.
- **Vencedor:** só é apontado se a faixa inteira ficar de um lado de 50%, ou seja, se a projeção estiver fora de
  49,3%–50,7%.
- **Registro:** cada minuto fica gravado. Depois comparamos com o resultado oficial e publicamos o erro, mesmo que
  seja ruim.

<!-- phase2:end -->
A projeção (fase 2) tem um pré-registro próprio, selado: o hash dele foi publicado antes da eleição e o conteúdo foi revelado em 28/10/2026. <!-- phase2 -->

**Auditoria depois da eleição:**
- **Varredura:** todos os blocos de 10 minutos passam pelo mesmo teste "seção × vizinhas do prédio", com correção
  para muitos testes (Bonferroni).
- **Travamento definido de forma objetiva:** 10 minutos ou mais sem o arquivo nacional mudar enquanto as urnas
  continuam chegando. O coletor registra isso.
- **Pausas na recepção** de 5 minutos ou mais são reportadas.
- **Conferências exatas:** soma dos boletins = total oficial = o que foi divulgado ao vivo.

**Calibração no 2º turno de 2022:** nenhum bloco acusou nada, nem houve pausa na recepção. O teste se comporta
bem num 2º turno sem incidentes.

---

## 11. Onde estamos e o que falta

**Pronto:**
- auditoria completa do 1º turno de 2026, sem sinal de interferência nos votos e com a pausa de 27,5 min
  documentada;
- modelo de projeção, ensaiado em 2022 e testado fora da amostra em 2026; <!-- phase2 -->
- coletor ao vivo, testado com o 1º turno, com conciliação exata.

**Falta, antes de 25/10:**
1. ~~escolher o modelo do 2º turno e a margem~~: feito, rascunho em `PREREGISTRATION_ROUND2.md` (±0,7 ponto); <!-- phase2 -->
2. ~~ligar a projeção ao coletor~~: feito (`python -m tally live --election 6258 --interval 60 --project`); <!-- phase2 -->
3. **o autor revisar e congelar o pré-registro** (até 24/10);
4. no dia, ligar o coletor por volta das 16h55.

**Pendências menores:**
- corrigir o fuso por urna (as 60 falhas de horário do MT);
- revisar os 14 casos de urna repetida de 2022;
- ~~instalar o git e subir o projeto para o GitHub~~: feito (github.com/Wizen-Labs/tally-forensics).

**Decisões do autor:**
- se e como publicar os achados (a pausa de 27,5 min é factual, mas sensível; o enquadramento deve ser neutro);
- se envia uma pergunta formal ao TSE sobre o campo de recebimento e a pausa.
