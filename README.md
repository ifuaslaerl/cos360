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

O benchmark cria instâncias sintéticas com grafos em cadeia, esparsos e densos.
Compara os métodos de `scipy.optimize.linprog` e, quando instalados, os solvers
disponíveis via PuLP e OR-Tools. Cada combinação roda em um processo separado;
o CSV inclui a biblioteca, o solver, os tempos de montagem/solução e o pico RSS.
O RSS inclui o interpretador e as bibliotecas nativas, não apenas a memória
interna do solver.

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.benchmark --list-solvers
.venv/bin/python -m src.benchmark
```

Use `--solvers` com os IDs exibidos por `--list-solvers` para selecionar
backends específicos. `--methods` continua disponível como atalho para
métodos do SciPy.

```bash
.venv/bin/python -m src.benchmark \
  --sizes 10 50 100 \
  --datasets chain sparse dense \
  --solvers scipy/highs pulp/PULP_CBC_CMD ortools/GLOP \
  --repeats 3 \
  --output results/benchmark.csv
```

Por padrão, testa todos os solver IDs encontrados no ambiente. Os resultados
são comparados pelo custo ótimo; o benchmark para se algum divergir. A matriz
do modelo atual é densa, então instâncias maiores podem consumir memória e
tempo rapidamente.
Durante a execução, cada caso exibe seu progresso, tempo total e pico de RSS.
O PDLP é executado com tolerâncias absolutas e relativas de otimalidade de
`1e-8` para manter os custos comparáveis aos demais solvers.
Exceções durante a execução de um solver são gravadas com `status=error` e a
mensagem na coluna `error`; os demais casos continuam. O gerador de gráficos
ignora automaticamente essas linhas.

Também é possível controlar as execuções pela API Python ou testar um modelo
próprio. Cada receita é `(índice_do_insumo, índice_do_produto, quantidade)` e
a demanda unitária é aplicada ao último item:

```python
from src.benchmark import Benchmark

benchmark = Benchmark(output="results/custom.csv", seed=123)
resultados = benchmark.run(
    datasets=("sparse",),
    sizes=(100, 250),
    solvers=("scipy/highs-ds", "pulp/PULP_CBC_CMD", "ortools/GLOP"),
    repeats=5,
)

resultados_customizados = benchmark.run_instance(
    costs=[(5.0, 1.0), (8.0, 2.0)],
    recipes=[(0, 1, 0.5)],
    solvers=("scipy/highs", "pulp/PULP_CBC_CMD", "ortools/GLOP"),
    repeats=3,
)
```

Para gerar gráficos das execuções salvas no CSV:

```bash
.venv/bin/python -m src.plot_benchmark
```

Isso lê `results/benchmark.csv` e gera gráficos PNG de tempo (montagem,
solução e total) e memória adicional de pico em `results/plots/`. Para usar
outro arquivo ou pasta de saída, passe `--input caminho.csv` e
`--output-dir pasta`.

Para gerar uma análise estatística do CSV, com gráficos consolidados de tempo
total e memória RSS, taxa de sucesso e observações em Markdown:

```bash
.venv/bin/python -m src.analyze_benchmark
```

Cada gráfico de tempo/memória mostra, por solver e tamanho, a mediana e a faixa
mínimo–máximo sobre datasets e repetições, em escala logarítmica. Os resultados
são salvos em `results/analysis/`. O script aceita `--input` e `--output-dir`
para analisar outro CSV ou mudar a pasta de saída.

---

### Autores
    
Luís Rafael Sena e Aline Capucho
