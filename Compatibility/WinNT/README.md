# WinNT experimental

Esta camada permite executar programas PE/WinNT em ambiente de usuário do
Pineapple OS/OEM-X. Ela usa Wine como backend compatível e um prefixo separado;
não executa código reconstruído do kernel NT em ring 0.

Uso:

```sh
WINNT_EXPERIMENTAL=1 pineapple-winnt ./programa.exe
```

O material em `E:/reload 7/knw/kernel_export/reconstructed` é uma reconstrução
decompilada e a documentação dele informa que ainda faltam WDK, tipos, globais,
símbolos e correções semânticas. Ele não deve ser compilado ou misturado ao
kernel OEM-X sem licença, validação e adaptação completa. O caminho organizado
é usado como referência para uma futura camada ABI NT10 em user mode.

O objetivo desta etapa é oferecer uma experiência utilizável e reversível:
programas Windows ficam isolados no prefixo experimental, enquanto apps Linux
continuam usando a ABI nativa do OEM-X.
