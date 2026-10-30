# Projekt

Underhålls av kvällsgenomgången (`/kvall`). Du kan också redigera filen själv, eller berätta
om projekt i kvällschatten så läggs de till här.

Senaste veckogenomgång: aldrig

**Regel:** högst 3 projekt under Aktiva. Nya idéer hamnar under Idéer tills ett aktivt
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
- Klart när: thesisen om LLM-syntetiserad supervisory control är skriven och försvarad
- Status: VM 103 i homelabbet kör simuleringarna (v4_low_run1–3 klara). Champions presterar lika bra eller bättre än Weirs TD-MPC.
- Nästa steg: skriv ner jämförelsen mot TD-MPC (tabell + plot) och mejla Weir om resultatet
- Källor: Proxmox, Linux files, and Docker containers (local_b8d0d69c), berättat i kvällschatten
- Senast rörd: 2026-10-30

### Jobbsök
- Kategori: Livet
- Klart när: ett jobb är accepterat (start runt februari 2027)
- Status: nio ansökningar ute. Ericsson ISAC Technical Coordinator har gått vidare efter CV-screen och Alva Labs-testerna (logik 10/10).
- Nästa steg: förbered Ericsson-intervjun och caset. Skicka uppföljningar 4–5 nov, och för Bertin Exensor och Axis Embedded runt 7 nov.
- Källor: Job search: setup, new portals and first scrape (local_86df7705), Job search in your area (local_837d9446)
- Senast rörd: 2026-10-29

### Gnomon
- Kategori: Programmering
- Klart när: (oklart, fråga) hela kampanjen är spelbar från början till slut på Pages
- Status: Phase 3-innehållet (C1–C5) är mergat. B2, B3 och story beats är live. B1 är klar och taggad `p4b-b1` men inte mergad, och integratorn stannade mitt i C5 #12.
- Nästa steg: starta om integratorn så att den avslutar C5 #12 och mergar B1, och speltesta sedan
- Källor: Plan and start GNOMON Phase 1 from p0-done (local_cd725928), GNOMON integrator (local_1be153ad)
- Senast rörd: 2026-10-30

## Pausade

### Fish assistant
- Kategori: Elektronik
- Klart när: (oklart, fråga) fiskkretsen med ESP32 fungerar
- Status: kretsen är inte testad, och det är oklart om den ska ha två eller tre motorer
- Nästa steg: koppla ESP32 på breadboard och testa hela kretsen
- Källor: berättat på webbsidan
- Senast rörd: 2026-10-30

### Homelab
- Kategori: Programmering
- Klart när: (oklart, fråga) servern är stabil och övervakad på Homepage
- Status: OptiPlex med Proxmox, media-VM 102 och thesis-VM 103. Nätverkskortshänget är åtgärdat genom att TSO/GSO är avstängt.
- Nästa steg: installera thesis-status som systemd-tjänst och lägg till ett Homepage-kort
- Källor: Proxmox, Linux files, and Docker containers (local_b8d0d69c)
- Senast rörd: 2026-10-30

### Cosmic Encounter-bot
- Kategori: Programmering
- Klart när: boten är delad i forumet
- Status: koden är klar och pushad, och sidan är live
- Nästa steg: sätt delning till "anyone with the link" och posta länken i forumet
- Källor: Cosmic Encounter rules bot (local_5091d1f5)
- Senast rörd: 2026-10-26

### Ender 3 / Klipper
- Kategori: Elektronik
- Klart när: Ender 3 V2 kör Klipper från Pi Zero 2W
- Status: SKR Mini E3 tar inte emot firmware från SD-kortet
- Nästa steg: kolla kortversionen, döp filen till firmware.bin, kallstarta och leta efter FIRMWARE.CUR
- Källor: Klipper E3 board flashing issue (local_9c8e77da)
- Senast rörd: 2026-10-28

## Idéer

## Klara

### Kvittens
- Kategori: Programmering
- Klart när: todo-listan skrivs ut som bongar varje morgon och kvällsgenomgången fungerar
- Status: första versionen är byggd och används
- Källor: Kvittoskrivare för todo-lista (local_505b0e20)
- Klart: 2026-10-30
