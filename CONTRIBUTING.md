# Guia de Contribuição

Obrigado por considerar contribuir para o Discord Mod Bot! Este documento fornece diretrizes para contribuir com o projeto.

## 📋 Código de Conduta

Ao participar deste projeto, você concorda em manter um ambiente respeitoso e inclusivo para todos.

## 🚀 Como Contribuir

### Reportando Bugs

Antes de criar um issue, verifique se o bug já não foi reportado. Ao criar um novo issue, inclua:

- **Descrição clara** do problema
- **Passos para reproduzir** o bug
- **Comportamento esperado** vs **comportamento atual**
- **Versão do Python** e **discord.py**
- **Logs relevantes** (sem informações sensíveis)
- **Screenshots** se aplicável

### Sugerindo Melhorias

Para sugerir novas funcionalidades:

- Use o template de feature request
- Explique **por que** a funcionalidade é útil
- Forneça **exemplos de uso**
- Considere **alternativas** que você avaliou

### Pull Requests

1. **Fork** o repositório
2. **Clone** seu fork localmente
3. **Crie uma branch** para sua feature/fix:
   ```bash
   git checkout -b feature/minha-feature
   ```
4. **Faça suas alterações** seguindo as diretrizes de código
5. **Adicione testes** para novas funcionalidades
6. **Execute os testes** e garanta que passam:
   ```bash
   pytest
   ```
7. **Execute o linting**:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   ```
8. **Commit suas mudanças** com mensagens descritivas:
   ```bash
   git commit -m "feat: adiciona comando de timeout"
   ```
9. **Push para seu fork**:
   ```bash
   git push origin feature/minha-feature
   ```
10. **Abra um Pull Request** no repositório principal

## 📝 Diretrizes de Código

### Estilo de Código

- Seguimos **PEP 8** com algumas exceções
- Linha máxima de **120 caracteres**
- Use **black** para formatação automática
- Use **type hints** sempre que possível

### Estrutura de Código

```python
"""
Docstring do módulo explicando seu propósito.
"""

import discord
from discord.ext import commands
from typing import Optional

# Imports de terceiros primeiro
# Depois imports locais

class MeuCog(commands.Cog):
    """Docstring da classe."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="exemplo", description="Descrição clara")
    async def exemplo(self, interaction: discord.Interaction):
        """Docstring do método."""
        # Implementação
        pass
```

### Convenções de Nomenclatura

- **Classes**: `PascalCase` (ex: `ModerationCog`)
- **Funções/Métodos**: `snake_case` (ex: `check_permissions`)
- **Constantes**: `UPPER_SNAKE_CASE` (ex: `MAX_WARNINGS`)
- **Variáveis**: `snake_case` (ex: `user_id`)

### Docstrings

Use docstrings para todas as funções, classes e módulos:

```python
def parse_duration(duration_str: str) -> Optional[timedelta]:
    """
    Converte string de duração para timedelta.
    
    Args:
        duration_str: String no formato "10s", "5m", "2h", etc.
    
    Returns:
        timedelta se válido, None caso contrário.
    
    Examples:
        >>> parse_duration("1h")
        timedelta(hours=1)
    """
    pass
```

### Tratamento de Erros

- Use `try-except` para operações que podem falhar
- Log erros usando `structlog`
- Forneça mensagens de erro claras aos usuários
- Nunca exponha stack traces aos usuários

```python
try:
    await member.ban(reason=reason)
except discord.Forbidden:
    await logger.aerror("Sem permissão para banir")
    raise PermissionError("Não tenho permissão para banir este usuário.")
except Exception as e:
    await logger.aerror("Erro ao banir", error=str(e))
    raise
```

### Testes

- Escreva testes para novas funcionalidades
- Mantenha cobertura de testes acima de 70%
- Use `pytest` e `pytest-asyncio`
- Mock dependências externas (Discord API)

```python
@pytest.mark.asyncio
async def test_parse_duration():
    """Testa parse de duração."""
    assert parse_duration("1h") == timedelta(hours=1)
    assert parse_duration("invalid") is None
```

## 🔍 Processo de Review

1. **Automated checks** devem passar (CI/CD)
2. **Code review** por pelo menos um maintainer
3. **Testes** devem cobrir novas funcionalidades
4. **Documentação** deve ser atualizada se necessário

## 📚 Recursos

- [Documentação do discord.py](https://discordpy.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## 💬 Comunicação

- **Issues**: Para bugs e feature requests
- **Discussions**: Para perguntas e discussões gerais
- **Pull Requests**: Para contribuições de código

## 🎯 Áreas que Precisam de Ajuda

- [ ] Testes adicionais
- [ ] Documentação e exemplos
- [ ] Tradução para outros idiomas
- [ ] Otimização de performance
- [ ] Novas funcionalidades

## ✅ Checklist do Pull Request

Antes de submeter seu PR, verifique:

- [ ] Código segue as diretrizes de estilo
- [ ] Testes foram adicionados/atualizados
- [ ] Todos os testes passam
- [ ] Documentação foi atualizada
- [ ] Commits seguem o padrão conventional commits
- [ ] Branch está atualizada com main
- [ ] Não há conflitos de merge

## 🙏 Agradecimentos

Obrigado por contribuir para tornar este projeto melhor!
