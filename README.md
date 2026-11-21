# Otimização de Processos: Modelo Make-or-Buy Multiestágio

Repositório dedicado ao estudo, especificação formal, modelagem matemática e implementação computacional de um problema de **Programação Linear** em que se decide, para cada item de uma cadeia produtiva, quanto **usar do estoque**, **comprar** e **produzir** para atender a demanda ao menor custo.

Trabalho desenvolvido para a disciplina de **Otimização (COS360/COM361 - PESC/COPPE/UFRJ)**.
---
## Estrutura do Repositório
- **`Sintese.ipynb`**: Contém o Jupyter Notebook principal com a modelagem detalhada e a resolução computacional.
- **`src/engine.py`**: classe `MakeOrBuyModel`, que monta e resolve o PL.
- **`src/plots.py`**: gráficos do grafo e da função objetivo.
- **`src/benchmark.py`, `src/solver_backends.py`, `src/plot_benchmark.py`, `src/analyze_benchmark.py`**: comparação de tempo e memória entre solvers (material complementar).
---
## Exemplo de Uso
```python
from src.engine import MakeOrBuyModel
model = MakeOrBuyModel()
model.add_item("etileno", inventory=20, purchase_cost=3.0, production_cost=0.8)
model.add_item("propileno", purchase_cost=4.0, production_cost=1.0)
model.add_item("solvente", purchase_cost=9.0, production_cost=2.0)
model.add_item("polimero", demand=100, purchase_cost=30.0, production_cost=3.0)
model.add_recipe("etileno", "solvente", 0.6)
model.add_recipe("propileno", "solvente", 0.5)
model.add_recipe("solvente", "polimero", 0.7)
model.add_recipe("etileno", "polimero", 0.4)
print(model.solve().total_cost)  # 524.6
```
---
## Como Executar
1. Clone o repositório:
   ```bash
   git clone <url-do-repositório>
   cd cos360
   ```
2. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
3. Abra o Jupyter Notebook correspondente.
---
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
