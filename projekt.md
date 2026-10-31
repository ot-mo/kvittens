# Projekt

Underhålls av kvällsgenomgången (`/kvall`). Du kan också redigera filen själv, eller berätta
om projekt i kvällschatten så läggs de till här.

Senaste veckogenomgång: 2026-10-31

**Regel:** högst 5 projekt under Aktiva. Nya idéer hamnar under Idéer tills ett aktivt
projekt är klart eller pausas. Målet är att göra klart, inte att börja på nytt.

## Aktiva

<!-- Mall:
### Projektnamn
- Kategori: Programmering / Elektronik / Kreativt / Livet
- Klart när: en mening om vad som räknas som färdigt
- Status: var projektet står nu
- Nästa steg: det konkreta nästa steget
- Källor: sessionstitlar (local_…) eller "berättat i kvällschatten"
- Senast rörd: ÅÅÅÅ-MM-DD
-->

### Thesis
- Kategori: Livet
- Klart när: exjobbet är inlämnat och presenterat, i januari 2027
- Deadlines: tester och benchmarking klara runt 2026-11-30, inlämning och presentation i januari 2027
- Status: VM 103 i homelabbet kör simuleringarna (v4_low_run1–3 klara). Fair comparison mot Weirs TD-MPC är körd, och LLM-koden ser fortfarande bra ut. Jämförelsen är nedskriven och Weir är mejlad.
- Nästa steg: planera vilka tester och benchmarks som återstår fram till 30 nov
- Källor: Proxmox, Linux files, and Docker containers (local_b8d0d69c), berättat i kvällschatten
- Senast rörd: 2026-10-31

### Jobbsök
- Kategori: Livet
- Klart när: ett jobb är accepterat (start runt februari 2027)
- Status: tio ansökningar ute, senast Arm Graduate ML Software Engineer i Lund (31 okt). Ericsson ISAC (ECP) har gått vidare efter testerna. Förberedelsen är klar och vi väntar på en intervjuinbjudan. Ericsson SW Developer (BBI, Req 792926) är skriven men inte skickad.
- Nästa steg: skicka uppföljningar på ansökningarna från 25 okt och skicka Ericsson SW Developer. Följ upp Bertin Exensor och Axis Embedded runt 7 nov och Arm runt 10 nov. Deadlines: Axis OS Security 17 nov, 3Shape Graduate 15 dec.
- Källor: Job search: setup, new portals and first scrape (local_86df7705), Job search in your area (local_837d9446), ISAC/RAN basics and examples (local_61c2da36)
- Senast rörd: 2026-10-31

### Gnomon
- Kategori: Programmering
- Klart när: Phase 4 är klar enligt TECH_DESIGN §8.7: alla C5-berättelseförfrågningar är mergade, speltestrundorna är gjorda, README är omskriven och spelet är släppt på GitHub Pages
- Status: B1, B4 (gear-krav i Elden Ring-stil), C5 #12, startquesten i Hollowmere och de sex krafterna är live på ot-mo.github.io/gnomon. Två kompisar har fått länken för att speltesta. Kvar för integratorn: C5 #10, #7 och #8 (Vesper och sluten, så spelet har inget slut än) och resten av #13.
- Nästa steg: skriv ett speltestformulär till kompisarna, gör en egen speltestrunda och läs igenom namn och texter
- Källor: Gnomon (local_1b519c81), GNOMON integrator (local_1be153ad), Plan and start GNOMON Phase 1 from p0-done (local_cd725928), GNOMON B4 (local_9e3b1429)
- Senast rörd: 2026-10-31

### Homelab
- Kategori: Programmering
- Klart när: (oklart, fråga) servern är stabil och övervakad på Homepage
- Status: OptiPlex med Proxmox, media-VM 102 och thesis-VM 103. Nätverkskortshänget är åtgärdat genom att TSO/GSO är avstängt. thesis-status (:8800) är installerad och syns på Homepage, och pve-temps (:8801) är installerad.
- Nästa steg: sätt upp backup för VM 102 och 103 så att thesis-datan är skyddad. Sedan pve-temps-kortet på Homepage och Tailscale.
- Källor: Proxmox, Linux files, and Docker containers (local_b8d0d69c)
- Senast rörd: 2026-10-31

### Ender 3 / Klipper
- Kategori: Elektronik
- Klart när: Ender 3 V2 kör Klipper från Pi Zero 2W
- Status: SKR Mini E3 tar inte emot firmware från SD-kortet
- Nästa steg: kolla kortversionen, döp filen till firmware.bin, kallstarta och leta efter FIRMWARE.CUR
- Källor: Klipper E3 board flashing issue (local_9c8e77da)
- Senast rörd: 2026-10-28

## Pausade

### Fish assistant
- Kategori: Elektronik
- Klart när: (oklart, fråga) fiskkretsen med ESP32 fungerar
- Status: kretsen är inte testad, och det är oklart om den ska ha två eller tre motorer
- Nästa steg: koppla ESP32 på breadboard och testa hela kretsen
- Källor: berättat på webbsidan
- Senast rörd: 2026-10-30

### Cosmic Encounter-bot
- Kategori: Programmering
- Klart när: boten är delad i forumet
- Status: koden är klar och pushad, och sidan är live
- Nästa steg: sätt delning till "anyone with the link" och posta länken i forumet
- Källor: Cosmic Encounter rules bot (local_5091d1f5)
- Senast rörd: 2026-10-26

### Korsordsappen (KorsordSve)
- Kategori: Programmering
- Klart när: ett riktigt korsord går att bygga från början till slut och skriva ut eller exportera som en ren PNG
- Status: React-editor för svenska pilkorsord (och amerikansk layout), live på ot-mo.github.io/KorsordSve. Den har bilder, pilar, zoner, ångra och import/export. Utskriften är fixad och PNG-export av korsord och facit fungerar.
- Nästa steg: bygg ett helt korsord, exportera och skriv ut det, och rätta det som skaver
- Källor: Crossword app using REA (local_6360f4dd)
- Senast rörd: 2026-10-23

### Filetree-mod
- Kategori: Programmering
- Klart när: modden är installerad och fungerar i alla sessioner
- Status: en "Files"-panel bredvid chatten. Den är färdig och testad men ligger bara i en sessionsbunden dev-mods-mapp, så den kan försvinna.
- Nästa steg: kopiera den till en egen mapp eller ett marketplace-repo, installera den och testa i en projektsession
- Källor: Filetree mod setup (local_4826577d)
- Senast rörd: 2026-10-09

## Idéer

## Klara

### Kvittens
- Kategori: Programmering
- Klart när: todo-listan skrivs ut som bongar varje morgon och kvällsgenomgången fungerar
- Status: första versionen är byggd och används
- Källor: Kvittoskrivare för todo-lista (local_505b0e20)
- Klart: 2026-10-30
