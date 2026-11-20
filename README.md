# Otimização de Processos: O Problema da Mistura e Variações

Repositório dedicado ao estudo, especificação formal, modelagem matemática e implementação computacional do **Problema da Mistura** e suas extensões avançadas em Pesquisa Operacional e Engenharia de Processos.

Trabalho desenvolvido para a disciplina de **Otimização (COS360/COM361 - PESC/COPPE/UFRJ)**.

---

## Estrutura do Repositório

- **`notebooks/`**: Contém o Jupyter Notebook principal com a modelagem detalhada e a resolução computacional.
- **`docs/`**: Documentação complementar, especificação formal e taxonomia.
- **`src/`**: Módulos auxiliares em Python com as formulações.

---

## Conteúdo do Guia e Taxonomia

O projeto pretende abordar o problema base e suas principais evoluções estruturais:

1. [ ] **Problema Base:** Minimização de custos de matérias-primas atendendo a demandas e especificações de qualidade.
2. [ ] **Redes de Fluxo Generalizado (GNF):** Tratamento de perdas e ganhos estequiométricos em grafos de conversão.
3. [ ] **Custos Fixos e Lotes Mínimos (MIP):** Inclusão de variáveis binárias para ativação de rotas e custos de *setup*.
4. [ ] **Problema do Pooling (NLP):** Abordagem de misturas multiestágio com não-linearidades bilineares e perda de convexidade.
5. [ ] **Síntese de Processos (MINLP):** Otimização topológica de superestruturas industriais.

---

## Como Executar

1. Clone o repositório:
   
   ```bash
   git clone https://github.com/seu-usuario/blending-process-optimization.git
   ```
   
2. Instale as dependências:
    
    ```bash
    pip install -r requirements.txt
    ```

3. Abra o Jupyter Notebook correspondente na pasta notebooks/.

## Benchmark de tempo e memória

O benchmark cria instâncias sintéticas com grafos em cadeia, esparsos e densos e
compara os métodos `highs`, `highs-ds` e `highs-ipm`. Cada combinação roda em
um processo separado; o CSV registra tempo de montagem, tempo de solução, pico
de RSS do processo e aumento do pico durante a execução do modelo. O RSS inclui
o interpretador e as bibliotecas nativas, portanto é uma medida do processo,
não apenas da memória interna do solver.

```bash
.venv/bin/python -m src.benchmark
```

Para controlar o tamanho, o número de repetições ou as estruturas testadas:

```bash
.venv/bin/python -m src.benchmark \
  --sizes 10 25 50 100 \
  --datasets chain sparse dense \
  --methods highs highs-ds highs-ipm \
  --repeats 5 \
  --output results/benchmark.csv
```

O padrão executa 81 casos pequenos (10, 25 e 50 itens; três estruturas;
três métodos; três repetições). O método `highs` pode selecionar internamente
um algoritmo; `highs-ds` e `highs-ipm` forçam dual simplex e ponto interior.
Os métodos são comparados pelo custo ótimo, e o benchmark falha se os
resultados divergirem. A matriz do modelo atual é densa, então instâncias
maiores podem consumir memória e tempo rapidamente.
Durante a execução, cada caso exibe seu progresso, tempo total e pico de RSS.

Também é possível controlar as execuções pela API Python ou testar um modelo
próprio. Cada receita é `(índice_do_insumo, índice_do_produto, quantidade)` e
a demanda unitária é aplicada ao último item:

```python
from src.benchmark import Benchmark

benchmark = Benchmark(output="results/custom.csv", seed=123)
resultados = benchmark.run(
    datasets=("sparse",),
    sizes=(100, 250),
    methods=("highs-ds", "highs-ipm"),
    repeats=5,
)

resultados_customizados = benchmark.run_instance(
    costs=[(5.0, 1.0), (8.0, 2.0)],
    recipes=[(0, 1, 0.5)],
    methods=("highs", "highs-ipm"),
    repeats=3,
)
```

---

### Autores
    
Luís Rafael Sena e Aline Capucho
