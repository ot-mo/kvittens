# Kvittens

En egen todo-lista som varje morgon skriver ut dagens uppgifter som restaurangbongar på en
kvittoskrivare. Sätt lapparna i bongskenan, och när en uppgift är klar river du ner lappen
och slänger den.

- **Webbgränssnitt** på `/` för att lägga till och bocka av uppgifter
- **REST-API** på `/api/...` så att andra appar och skript kan skriva till listan
- **MCP-server** på `/mcp` så att Claude kan läsa, lägga till och skriva ut uppgifter
- **Morgonutskrift** kl `PRINT_TIME`: de viktigaste öppna uppgifterna som inte redan sitter i skenan
- **QR-kod på varje bong**: skanna med mobilen för att markera uppgiften som klar

## Vad hamnar på morgonbongarna?

Öppna uppgifter som inte redan skrivits ut och som inte har en deadline längre fram.
Försenade och dagens uppgifter kommer först, sedan sorteras resten efter prioritet.
Högst `MAX_TICKETS` per morgon. En lapp som redan sitter i skenan skrivs inte ut igen.
Om du tappar bort en lapp kan du skriva ut den igen med 🖨-knappen.

## Kom igång på hemmaservern (Docker)

```bash
cp .env.example .env      # fyll i API_KEY och PUBLIC_URL
docker compose up -d --build
```

Öppna sedan `http://<serverns-ip>:8080`. All data ligger i `./data`: databasen, de
renderade bongarna och hemligheten för QR-länkarna. Det är den mappen du ska ta backup på.

Utan skrivare kör du med `PRINTER_TYPE=preview`. Då sparas bongarna bara som bilder i
`data/tickets/`, och du kan se dem via 👁-knappen i webbgränssnittet.

## Köra lokalt utan Docker

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt     # Windows: .venv\Scripts\pip
.venv/bin/uvicorn app.main:app --port 8080
```

## Koppla in skrivaren

**Nätverksskrivare (rekommenderas):** Koppla skrivaren till routern och ge den en fast IP-adress
i routern. Skriv sedan ut skrivarens självtest (håll inne FEED när du slår på den) för att se
adressen. Ställ därefter in:

```
PRINTER_TYPE=network
PRINTER_HOST=192.168.1.50
```

**USB:** Ta reda på vendor- och product-id med `lsusb` (t.ex. `04b8:0e28` för Epson). Fyll i
`USB_VENDOR=0x04b8` och `USB_PRODUCT=0x0e28` och avkommentera `devices` i `docker-compose.yml`.

Använder du 58 mm-papper sätter du `PAPER_WIDTH_PX=384`.

## Koppla Claude till listan

**Claude Code** (fungerar direkt i hemnätverket):

```bash
claude mcp add --transport http kvittens http://<serverns-ip>:8080/mcp --header "Authorization: Bearer <API_KEY>"
```

Sedan kan du säga till exempel: *"lägg till att jag ska ringa Skatteverket imorgon, hög prio"*
eller *"vilka bongar skrivs ut imorgon bitti?"*

**Claude-appen / claude.ai:** Egna connectors anropas från Anthropics moln. Servern måste
därför gå att nå från internet via HTTPS, till exempel genom Cloudflare Tunnel eller
Tailscale Funnel. Connectors stödjer inte egna headers, så det kräver också OAuth-inloggning.
Det är ett naturligt nästa steg att bygga.

MCP-verktyg: `list_tasks`, `add_task`, `update_task`, `complete_task`, `reopen_task`,
`delete_task`, `preview_morning_tickets`, `print_tickets`.

## REST-API för andra appar

Alla anrop kräver headern `X-API-Key: <API_KEY>` eller `Authorization: Bearer <API_KEY>`.
Interaktiv dokumentation finns på `/docs`.

```bash
# Lägg till
curl -X POST http://server:8080/api/tasks -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
     -d '{"title": "Betala hyran", "project": "Hem", "priority": 2, "due": "2026-11-28", "source": "hemautomation"}'

# Lista öppna
curl http://server:8080/api/tasks -H "X-API-Key: $KEY"
```

| Metod  | Sökväg                        | Gör                                          |
|--------|-------------------------------|----------------------------------------------|
| GET    | `/api/tasks?status=open`      | Lista (`open`, `done`, `all`, `&project=`)   |
| POST   | `/api/tasks`                  | Skapa                                        |
| PATCH  | `/api/tasks/{id}`             | Ändra                                        |
| POST   | `/api/tasks/{id}/done`        | Markera klar                                 |
| POST   | `/api/tasks/{id}/reopen`      | Öppna igen (skrivs ut nästa morgon)          |
| DELETE | `/api/tasks/{id}`             | Ta bort                                      |
| POST   | `/api/tasks/{id}/print`       | Skriv ut bongen nu                           |
| GET    | `/api/tasks/{id}/ticket.png`  | Bongen som bild                              |
| GET    | `/api/morning`                | Nästa utskriftstid och vilka bongar som kommer |
| POST   | `/api/morning/print`          | Kör morgonutskriften direkt                  |

Prioritet: 1 = brådskande, 2 = hög, 3 = normal, 4 = låg. Projektet visas som "BORD" på bongen.
