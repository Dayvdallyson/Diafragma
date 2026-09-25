Fase 0 — Fundação

Objetivo: ambiente pronto e o domínio desenhado no papel.

Pronto quando:

Você tem um repositório com a estrutura de pastas decidida por você.
Existe um diagrama (pode ser à mão) das entidades: cliente, produto, unidade física, reserva, pagamento.
Existem de 30 a 50 produtos fictícios, com descrição e especificações.

Pesquise:

A diferença entre produto (o modelo "Sony A7 III") e unidade (a câmera de número de série X). Você vai precisar das duas.
Como modelar reservas por intervalo de datas.

Armadilha: começar pelo LLM. Comece pelo domínio.

Fase 1 — Banco e o problema da concorrência

Objetivo: reservar uma unidade sem nunca gerar reserva duplicada.

Pronto quando: você escreve um script que dispara 20 tentativas simultâneas de reservar a mesma câmera nas mesmas datas e exatamente uma dá certo.

Pesquise:

SELECT ... FOR UPDATE
Níveis de isolamento de transação no Postgres
EXCLUDE constraint com tstzrange ou daterange
Idempotency keys

Armadilha: checar disponibilidade e depois inserir em duas etapas separadas. Isso é uma race condition clássica.

Desafio extra: reserva em estado "pendente" que expira em 15 minutos se não for paga. Por enquanto, sem fila: só modele o estado.

Fase 2 — Primeiro agente de voz

Objetivo: conversar por voz com a agente, que consulta o banco da Fase 1.

Pronto quando: você pergunta "tem alguma câmera livre sábado?" e ela responde falando, com base em dados reais.

Pesquise:

Documentação do LiveKit Agents: o quickstart de voice agent e a parte de function tools
As etapas do pipeline: STT, LLM e TTS
VAD
Turn detection
Opções de STT e TTS com bom português

Armadilhas:

O LLM inventar disponibilidade. A regra é: se não veio de uma ferramenta, ela não sabe.
Respostas longas demais para voz.

Desafio extra: meça quanto tempo passa entre você parar de falar e ouvir o primeiro som. Anote esse número, porque ele vai ser seu indicador principal para sempre.

Fase 3 — Soar humana

Objetivo: a conversa parecer atendimento de verdade.

Pronto quando:

Você consegue interromper a agente.
Ela diz algo enquanto uma ferramenta demora ("deixa eu ver aqui…").
Ela fala preços e datas por extenso de forma natural.
Ela sempre confirma antes de reservar.

Pesquise:

Interruptions e allow_interruptions no LiveKit
Normalização de texto para TTS (text normalization)
Técnicas de prompting para voz

Armadilha: tentar resolver tudo no prompt. Algumas coisas, como converter números em texto falado, são código determinístico.

Fase 4 — RAG sobre o catálogo

Objetivo: responder perguntas técnicas, como "essa lente serve na minha Canon R6?".

Pronto quando:

Você tem um conjunto de umas 40 perguntas com as respostas esperadas.
Você mede recall@k e fidelidade antes e depois de cada melhoria: primeiro só busca vetorial, depois busca híbrida, depois reranking.

Pesquise:

pgvector
Estratégias de chunking
BM25 e full-text search no Postgres
Reciprocal Rank Fusion
Cross-encoder rerankers
Métricas de avaliação de RAG

Armadilha: avaliar "no olho". Sem números, você não sabe se melhorou.

Fase 5 — Sub-agentes e memória

Objetivo: separar responsabilidades entre catálogo, reserva e pagamento, e fazer a agente lembrar do cliente.

Pronto quando:

Cada sub-agente devolve JSON validado por schema.
A atendente só verbaliza o que recebeu.
Quando você liga de novo, ela sabe o que você alugou da última vez.

Pesquise:

Structured outputs
Pydantic ou JSON Schema
Diferença entre workflow e agente
Memória de curto e de longo prazo

Armadilha: multi-agente por modismo. Se um sub-agente não justifica existir, ele vira só uma função.

Fase 6 — Assíncrono: WhatsApp e ciclo de vida

Objetivo: tirar do caminho em tempo real tudo o que não precisa estar nele.

Pronto quando:

Um áudio recebido no WhatsApp entra numa fila e é processado por um worker, e o cliente recebe um áudio de resposta.
As reservas pendentes expiram sozinhas.
O webhook de pagamento confirma a reserva.

Pesquise:

SQS: visibility timeout, dead-letter queue, entrega at-least-once
Idempotência em consumidores
API do WhatsApp Business

Armadilha: processar a mesma mensagem duas vezes e cobrar ou reservar em dobro. Sua fila vai entregar mensagens duplicadas.

Fase 7 — Fine-tuning do classificador de intenção

Objetivo: um modelo pequeno que, a partir da fala do cliente, devolve a intenção e os dados extraídos em JSON, por exemplo {intencao, produto, data_inicio, data_fim}.

Pronto quando: você tem uma tabela comparando o modelo base, o modelo com fine-tuning e um LLM grande com prompt, em F1, validade do JSON, latência e custo.

Pesquise:

Hugging Face transformers, datasets e peft
LoRA e QLoRA
Tokenização
Divisão treino/validação/teste
Dados sintéticos com revisão humana

Armadilha: vazar exemplos de teste no treino, o que gera números bonitos e falsos. Use as conversas reais que você acumulou nas fases anteriores.

Fase 8 — AWS, CI/CD e observabilidade

Objetivo: tudo rodando na nuvem, com deploy automático e visível.

Pronto quando:

Um push na main roda os testes e as avaliações, gera a imagem e faz o deploy.
Você tem um painel com latência por etapa (STT, LLM e TTS), custo por atendimento e erros de ferramentas.

Pesquise:

ECS Fargate versus Lambda (por que o agente de voz não cabe em Lambda?)
ECR
RDS
IAM com privilégio mínimo
GitHub Actions com OIDC para a AWS (sem chave fixa)
OpenTelemetry
CloudWatch

Armadilha: credenciais no código ou em variável commitada.
