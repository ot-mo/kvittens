# Kvittens

En egen todo-lista som varje morgon skriver ut dagens uppgifter som restaurangbongar på en
kvittoskrivare. Sätt lapparna i bongskenan, och när en uppgift är klar river du ner lappen
och slänger den.

- **Webbgränssnitt** på `/` för att lägga till och bocka av uppgifter
- **REST-API** på `/api/...` så att andra appar och skript kan skriva till listan
- **MCP-server** på `/mcp` så att Claude kan läsa, lägga till och skriva ut uppgifter
- **Morgonutskrift** kl `PRINT_TIME`: de viktigaste öppna uppgifterna som inte redan sitter i skenan
- **Kvällsgenomgång i Claude Code**: berätta vad du gjort idag, så läser Claude dina
  projektchattar, uppdaterar listan och bestämmer vad du ska fokusera på
- **Dagbok** med kvällsgenomgångarna och dina egna anteckningar

## Vad hamnar på morgonbongarna?

Öppna uppgifter som inte redan skrivits ut och som inte har en deadline längre fram.
Försenade och dagens uppgifter kommer först, sedan sorteras resten efter prioritet.
Högst `MAX_TICKETS` per morgon. En lapp som redan sitter i skenan skrivs inte ut igen.
Om du tappar bort en lapp kan du skriva ut den igen med 🖨-knappen.

## Kvällsgenomgången i Claude Code

Listan sköts av en kvällssession i Claude-appen (Code-fliken), så du behöver nästan aldrig
skriva uppgifter själv. Ingen API-nyckel behövs, det körs på din vanliga Claude-prenumeration.

1. Öppna en ny session i Kvittens-mappen och skriv `/kvall`, gärna direkt följt av vad du
   gjort idag. Till exempel: `/kvall lödde klart förstärkaren och skickade två ansökningar`.
2. Sessionen läser listan, dagboken och dina projektchattar i sidomenyn, alltså de som är
   fästa och de i grupperna Programing Projects, Electronics Projects, Creative projects
   och Life projects.
3. Den bockar av det du gjort, lägger till konkreta nästa steg och bestämmer 1–3 saker
   att fokusera på. Imorgon bitti skrivs de ut som bongar.
4. Vill du ändra något säger du bara det i chatten.

Instruktionerna finns i [`.claude/skills/kvall/SKILL.md`](.claude/skills/kvall/SKILL.md),
och kopplingen till servern i [`.mcp.json`](.mcp.json). Sätt de här två miljövariablerna
i Windows, så att Claude Code hittar servern:

```
KVITTENS_URL=http://<serverns-ip>:8080
KVITTENS_API_KEY=<samma som API_KEY i .env>
```

Varje genomgång sparas i dagboken (fliken **Dagbok** på webbsidan) tillsammans med vad som
ändrades. Där finns också en **Ångra**-knapp. Under dagen kan du skriva korta anteckningar
i samma flik, och kvällssessionen läser dem.

## Kom igång på hemmaservern (Docker)

```bash
cp .env.example .env      # fyll i API_KEY
docker compose up -d --build
```

Öppna sedan `http://<serverns-ip>:8080`. All data ligger i `./data`: databasen med
uppgifter och dagbok, samt de renderade bongarna. Det är den mappen du ska ta backup på.

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

**Claude Code** (fungerar direkt i hemnätverket): Sessioner i Kvittens-mappen kopplas upp
automatiskt via `.mcp.json`. Vill du nå listan från alla sessioner lägger du till den en gång:

```bash
claude mcp add --scope user --transport http kvittens http://<serverns-ip>:8080/mcp --header "Authorization: Bearer <API_KEY>"
```

Sedan kan du säga till exempel: *"lägg till att jag ska ringa Skatteverket imorgon, hög prio"*
eller *"vilka bongar skrivs ut imorgon bitti?"*

**Claude-appen / claude.ai:** Egna connectors anropas från Anthropics moln. Servern måste
därför gå att nå från internet via HTTPS, till exempel genom Cloudflare Tunnel eller
Tailscale Funnel. Connectors stödjer inte egna headers, så det kräver också OAuth-inloggning.
Det är ett naturligt nästa steg att bygga.

MCP-verktyg: `list_tasks`, `add_task`, `update_task`, `complete_task`, `reopen_task`,
`delete_task`, `read_journal`, `write_journal_entry`, `preview_morning_tickets`, `print_tickets`.

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
| GET    | `/api/journal`                | Dagboksinlägg, nyast först                   |
| POST   | `/api/journal`                | Ny anteckning `{"text": "..."}`             |
| POST   | `/api/journal/{id}/undo`      | Ångra ändringarna från ett inlägg            |

Prioritet: 1 = brådskande, 2 = hög, 3 = normal, 4 = låg. Projektet visas som "BORD" på bongen.
