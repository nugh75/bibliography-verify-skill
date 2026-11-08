# bibliography-verify

Use [SKILL.md](SKILL.md) for the audit commands, provider selection and
interpretation of results.

## PDF Server (biblioteca open-access via nginx)

Se la repository ha una cartella `schede/` con PDF di letteratura, si serve
staticamente tramite nginx sotto `/pdf/` — niente VPN, niente server Python.

### Configurazione nginx

Aggiungere dentro il `server {}` del virtual host:

```nginx
location /pdf/ {
    alias /home/nugh75/Prin-article-counslorbot/schede/;
    autoindex on;
    index index.html;
}
```

Dopo aver editato:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Permessi

Se nginx (`www-data`) non riesce a leggere i file dentro `/home/nugh75/`:

```bash
sudo usermod -aG nugh75 www-data
```

### Makefile

```makefile
.PHONY: pdf-open
pdf-open:
	@echo "Apri https://code.ai4educ.org/pdf/"
	@xdg-open "https://code.ai4educ.org/pdf/" 2>/dev/null || true
```

### Script autonomo

`schede/nginx-add-pdf-route.sh` — copia il config nginx già pronto, testa e ricarica:

```bash
sudo bash schede/nginx-add-pdf-route.sh
```

### Replicare su un altro progetto

1. Servire i file statici con `location /pdf/ { alias /path/to/cartella/; ... }`
2. Se i file sono in `/home/nugh75/`, assicurarsi che `www-data` sia nel gruppo
   `nugh75` (`sudo usermod -aG nugh75 www-data`)
3. Ricaricare nginx
