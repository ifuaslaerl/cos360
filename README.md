# Otimização de Processos: O Problema da Mistura (Blending Problem) e Variações

Repositório dedicado ao estudo, especificação formal, modelagem matemática e implementação computacional do **Problema da Mistura** e suas extensões avançadas em Pesquisa Operacional e Engenharia de Processos.

Trabalho desenvolvido para a disciplina de **Otimização (COS360/COM361 - PESC/COPPE/UFRJ)**.

---

## Estrutura do Repositório

- **`notebooks/`**: Contém o Jupyter Notebook principal com a modelagem detalhada e a resolução computacional.
- **`docs/`**: Documentação complementar, especificação formal e taxonomia.
- **`src/`**: Módulos auxiliares em Python com as formulações (LP, MIP, NLP).

---

## Conteúdo do Guia e Taxonomia

O projeto pretende abordar o problema base e suas principais evoluções estruturais:

1. [ ] **Problema Base (Standard LP Blending):** Minimização de custos de matérias-primas atendendo a demandas e especificações de qualidade.
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

---

### Autores
    
Luís Rafael Sena e Aline Capucho
