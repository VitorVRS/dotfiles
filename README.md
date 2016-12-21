# dotfiles
:hankey: Meus arquivos de configuração pessoais

Este repositório dispõe de um aplicativo ```vrs``` que auxilia na gestão dos seus programas de uso pessoal e suas configurações.

## Utilização

```shell
cd /path/to/dotfiles_repo/
./vrs
```

### Comando ```install```

Irá perguntar quais programas/aplicações irão ser instalados na máquina.

> Os programas serão pré-definidos em um arquivo de configuração.

```shell
./vrs install
```

Executado o comando, será perguntado ao usuário se quer ou instalar o programa/aplicaçã informado.

### Comando ```configure```

Irá perguntar quais programas/aplicações serão configurados, por exemplo: copiar suas configurações pessoais do editor que utiliza para o novo local.

> As configurões dos programas serão pré-definidas em um diretório de configurações.

```shell
./vrs configure
```

Executado o comando, será perguntado ao usuário se quer configurar o programa/aplicação informado.