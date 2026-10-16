# AWX Phoenix EE Core

Imagen base: localhost/alma-awx-ee-core:candidate

Receptor validado: 1.6.1.

Para construir:

1. Obtener el binario Receptor 1.6.1 verificado.
2. Colocarlo en este directorio como receptor.
3. Ejecutar:

    podman build -t localhost/alma-awx-ee-core:receptor-fixed .

La imagen elimina el ENTRYPOINT heredado de ansible-runner.
El binario receptor no se almacena en Git.
