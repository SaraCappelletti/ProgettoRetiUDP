# Progetto di Reti - Server UDP
Sara Cappelletti  
Rachele Margutti
# User Guide
Per poter eseguire i file presenti all’interno di questo progetto è necessario
usare una versione di Python ≥ 3.8.  
Non è necessario installare alcun pacchetto aggiuntivo in quanto vengono
usati solo moduli presenti nella libreria standard di Python.
# Server
Per avviare il server è sufficiente il seguente comando:

```python3 server.py```
# Client
Tutti i comandi disponibili e i relativi argomenti sono disponibili tramite il comando `--help`.
## Comando LIST
```python3 client.py list```
## Comando PUT
```python3 client.py put nomefile /path/al/file```
## Comando GET
```python3 client.py get nomefile /path/in/cui/salvarlo```