# Manual rápido: Google, Drive e Colab

Para rodar o caderno `aprenda_apuracao_ao_vivo.ipynb`. Não é preciso instalar nada: tudo roda no navegador
(Chrome, Edge ou Firefox), num computador com internet. Celular não serve para o dia da eleição.

## 1. Conta Google (5 minutos, uma vez só)
Quem já tem Gmail pode pular para o passo 2.

1. Abra **accounts.google.com/signup**.
2. Preencha nome, data de nascimento, nome de usuário (o Gmail) e senha.
3. Confirme o número de celular quando pedir.
4. Pronto. A mesma conta dá acesso ao Gmail, ao **Google Drive** (15 GB grátis) e ao **Google Colab**.

> Use uma senha forte e ative a verificação em duas etapas (myaccount.google.com → Segurança).

## 2. Google Drive: a pasta de trabalho
O Drive guarda os resultados, porque o Colab apaga tudo quando a sessão termina.

- **Eduardo:** não precisa fazer nada. O caderno cria sozinho a pasta `tally_live_independent` no Drive.
- **Ajudantes:**
  1. O Eduardo compartilha a pasta `tally_live_independent` com o seu Gmail, como **Editor**.
  2. Abra **drive.google.com** → **Compartilhados comigo**.
  3. Clique com o botão direito na pasta → **Organizar → Adicionar atalho** → **Meu Drive**.

     Sem o atalho, o caderno não encontra a pasta.

## 3. Abrir o caderno no Colab
1. Baixe o arquivo `aprenda_apuracao_ao_vivo.ipynb` que o Eduardo enviou.
2. Abra **colab.research.google.com**, entrando com a sua conta Google.
3. Na janela que aparece, escolha **Fazer upload** e selecione o arquivo. Se a janela não aparecer, use
   **Arquivo → Fazer upload de notebook**.
4. O caderno passa a ficar salvo no seu Drive, na pasta **Colab Notebooks**. Nas próximas vezes, abra por lá.

## 4. Executar
1. Na **Parte 2 (Configurações)**:
   - **ajudantes** escrevem o primeiro nome em `AJUDANTE`, por exemplo `AJUDANTE = "pedro"`;
   - **o Eduardo** deixa vazio.
2. Clique na primeira célula de código e aperte **Shift + Enter**. Repita célula por célula, de cima para baixo,
   lendo as explicações.
3. Na célula do Drive, o Google pede autorização: escolha a sua conta e clique em **Permitir**.
4. A primeira vez demora cerca de **7 minutos** na Parte 8, porque baixa a base do 1º turno. Nas outras vezes leva
   segundos.
5. A **Parte 10 (Ensaio)** deve mostrar a projeção **51,01%**. Se mostrar, está tudo certo.

Atalho para rodar tudo de uma vez: **Ambiente de execução → Executar tudo**. Não use no treino, porque a Parte 12
fica rodando até as 21h.

## 5. No dia da eleição (25/10)
1. Às **16h30**, abra o caderno e, na Parte 2, mude para `ELEICAO = "6258"`.
2. Rode as células na ordem até a Parte 12 e deixe a Parte 12 rodando. Ela imprime uma linha a cada ciclo e para
   sozinha às 21h.
3. **Deixe a aba aberta e o computador ligado**, ligado na tomada e sem suspender. Se a aba fechar ou o Colab
   desconectar, abra de novo e rode tudo outra vez: nada se perde, porque está no Drive.
4. Os cartões aparecem no Drive, em `tally_live_independent/cards` (ajudantes: em `helpers/<nome>/cards`).
   **Cartão de ajudante não se publica.**
5. Para parar antes das 21h, clique no **■** ao lado da célula. O aviso `KeyboardInterrupt` é normal.

## Problemas comuns
| O que aparece | O que fazer |
|---|---|
| `NameError: ... is not defined` | Uma célula de cima não foi rodada. Use Ambiente de execução → Reiniciar sessão e rode de novo desde o início. |
| Muitos `429` ou "recuo" na Parte 12 | O programa já desacelera sozinho. Não rode mais de um caderno na mesma conta ou rede. |
| A pasta do Drive não aparece (ajudante) | Falta o atalho do passo 2. |
| "Não é possível conectar ao back-end" / sessão caiu | Conecte de novo (botão **Conectar**, no canto superior direito) e rode tudo de novo. |
| A projeção do ensaio não deu 51,01% | Mande o texto da tela para o Eduardo. |
