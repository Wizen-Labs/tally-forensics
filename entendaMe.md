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
| **Fora da amostra** | Testar em dados que não foram usados para construir o modelo |

---

## 10. O pré-registro do 2º turno (`PREREGISTRATION_ROUND2.md`)

São as regras escritas **antes** do dia 25, para que ninguém (nem nós) possa ajustar nada depois de ver o resultado.

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
- coletor ao vivo, testado com o 1º turno, com conciliação exata.

**Falta, antes de 25/10:**
3. **o autor revisar e congelar o pré-registro** (até 24/10);
4. no dia, ligar o coletor por volta das 16h55.

**Pendências menores:**
- corrigir o fuso por urna (as 60 falhas de horário do MT);
- revisar os 14 casos de urna repetida de 2022;
- ~~instalar o git e subir o projeto para o GitHub~~: feito (github.com/Wizen-Labs/tally-forensics).

**Decisões do autor:**
- se e como publicar os achados (a pausa de 27,5 min é factual, mas sensível; o enquadramento deve ser neutro);
- se envia uma pergunta formal ao TSE sobre o campo de recebimento e a pausa.
