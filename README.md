# Otimização de Processos: Modelo Make-or-Buy Multiestágio

Repositório dedicado ao estudo, especificação formal, modelagem matemática e implementação computacional de um problema de **Programação Linear** em que se decide, para cada item de uma cadeia produtiva, quanto **usar do estoque**, **comprar** e **produzir** para atender a demanda ao menor custo.

Trabalho desenvolvido para a disciplina de **Otimização (COS360/COM361 - PESC/COPPE/UFRJ)**.

---
## Estrutura do Repositório

### Modelo base (`Sintese_Base.ipynb`)
- **`src/legacy/engine.py`**: classe `MakeOrBuyModel`, monta e resolve o PL (um ingrediente por receita, com capacidades opcionais de compra/produção).
- **`src/legacy/plots.py`**: gráficos do grafo, breakdown de custo, sensibilidade e região viável.
- **`src/legacy/instances.py`**: gerador de instâncias aleatórias (`random_model`).

### Pipeline aplicado ao jogo Satisfactory (`Sintese.ipynb`)
- **`Datasets/Satisfactory/standardizer.py`**: converte o `Docs.json` do jogo em itens e receitas, com custo de compra via pontos do AWESOME Sink e custo de produção via energia da máquina × duração da receita.
- **`src/domain/`**: modelos de domínio (`Item`, `Recipe` com múltiplos insumos e receitas alternativas).
- **`src/optimization/`**: monta e resolve o PL via `scipy.optimize.linprog` (`OptimizationEngine`, `ScipySolverAdapter`).
- **`src/etl/`**: leitura, padronização e validação de datasets, geração de cenários e escrita de resultados.
- **`src/application/`**:
  - `pipeline_runner.py`: executa o pipeline completo sobre um ou mais cenários.
  - `generate_satisfactory_scenarios.py`: gera cenários sintéticos de demanda.
  - `generate_satisfactory_charts.py`: gera os gráficos (`results/satisfactory/graficos/`) a partir dos CSVs de execução.

---
## Exemplo de Uso — Modelo Base

```python
from src.legacy.engine import InfeasibleError, MakeOrBuyModel

model = MakeOrBuyModel()
model.add_item("etileno", inventory=60, purchase_cost=2.0, production_cost=2.5)
model.add_item("propileno", purchase_cost=3.0, production_cost=1.5)
model.add_item("solvente", demand=20, purchase_cost=2.5, production_cost=1.0)
model.add_item("aditivo", demand=40, purchase_cost=2.5, production_cost=1.0)
model.add_item("polimero", demand=100, purchase_cost=12.0, production_cost=3.0)
model.add_recipe("etileno", "solvente", 0.6)
model.add_recipe("propileno", "solvente", 0.5)
model.add_recipe("etileno", "aditivo", 0.3)
model.add_recipe("propileno", "aditivo", 0.8)
model.add_recipe("solvente", "polimero", 0.7)
model.add_recipe("etileno", "polimero", 0.4)
print(model.solve().total_cost)

model.set_production_capacity("polimero", 60)
print(model.solve().total_cost)

model.set_purchase_capacity("polimero", 30)
try:
    model.solve()
except InfeasibleError:
    print("sem plano viável")
```

Para sortear instâncias com itens `p1, ..., pN` (receitas, demandas, estoques, custos e capacidades de produção aleatórios, com semente para reprodução):
```python
from src.legacy.instances import random_model
model = random_model(n_items=10, seed=1)
```

Os gráficos são funções de `src/legacy/plots.py` que recebem o modelo: `plot_graph`, `plot_cost_breakdown`, `plot_sensitivity` (demanda, estoque, custos ou capacidades), `plot_demand_sensitivity` e `plot_feasible_region`. Eles são exibidos na tela e não são salvos em arquivo.

---
## Exemplo de Uso — Pipeline Satisfactory

```bash
.venv/bin/python -m src.application.pipeline_runner
.venv/bin/python -m src.application.generate_satisfactory_charts
```

Os resultados por cenário ficam em `results/satisfactory/scenarios/`, e os gráficos consolidados em `results/satisfactory/graficos/`.

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
3. Abra o Jupyter Notebook correspondente (`Sintese_Base.ipynb` ou `Sintese.ipynb`).

---
### Autores

Luís Rafael Sena e Aline Capucho
