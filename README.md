# Volné kurty – padel Praha

Každých ~10 minut zkontroluje obsazenost krytých padelových kurtů v Praze,
ukáže ji na webu (funguje jako appka na iPhonu) a pošle zprávu na Telegram,
když se uvolní něco, co bylo obsazené, v tvých časech.

**Sledovaná centra:** OnePadel Zličín, Padel Powers Smíchov, Padel Džus Hostivař,
Padelmanie, Padel Neride, Písečná (jen 2 zastřešené kurty).

**Tvoje časy:** Po, Út, Čt, Pá 18–22 · So, Ne 10–13 a od 15 · středa ne ·
hra aspoň 90 min (ideálně 120) · 14 dní dopředu.
Všechno se mění v `checker/config.py`.

---

## Nasazení (cca 10 minut, jednou)

### 1. Telegram bot

1. V Telegramu napiš **@BotFather** → `/newbot` → zadej jméno (třeba „Padel Praha“)
   a uživatelské jméno končící na `bot`.
2. BotFather ti pošle **token** (vypadá jako `123456789:AAH...`). Ulož si ho.
3. Napiš svému novému botovi cokoliv (třeba „ahoj“), jinak ti nemůže psát.
4. Otevři v prohlížeči `https://api.telegram.org/bot<TOKEN>/getUpdates`
   (místo `<TOKEN>` vlož svůj token). V odpovědi najdi `"chat":{"id":123456789`.
   To číslo je tvoje **chat ID**.

### 2. GitHub repozitář

1. Na github.com si založ účet (pokud nemáš) a vytvoř **nový repozitář**, třeba
   `padel-checker`. Dej mu **Public**. U veřejných repozitářů jsou Actions zdarma
   bez limitu. U privátních máš 2 000 minut měsíčně a kontrola každých 10 minut
   jich spotřebuje přes 4 000. V kódu nic citlivého není, tokeny jsou v Secrets.
2. Nahraj obsah téhle složky: na stránce repozitáře **Add file → Upload files**,
   přetáhni všechny soubory a složky (včetně `.github`) a dej **Commit changes**.
   > Složka `.github` začíná tečkou a na Macu je skrytá. Ve Finderu ji zobrazíš
   > zkratkou **Cmd + Shift + .**

### 3. Tajné klíče

V repozitáři **Settings → Secrets and variables → Actions → New repository secret**:

| Název | Hodnota |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token od BotFathera |
| `TELEGRAM_CHAT_ID` | číslo z kroku 1.4 |

### 4. Zapnout dashboard (GitHub Pages)

**Settings → Pages → Build and deployment**: Source **Deploy from a branch**,
Branch **main**, složka **/docs** → Save.
Za minutu ti GitHub ukáže adresu typu `https://<tvuj-ucet>.github.io/padel-checker/`.

### 5. Spustit

1. **Actions** → pokud se ptá, potvrď **I understand my workflows, go ahead and enable them**.
2. **Test Telegramu → Run workflow** → během chvíle ti má přijít zpráva
   „Telegram funguje ✔“.
3. **Kontrola kurtů → Run workflow** → první běh jen nasbírá výchozí stav
   (notifikace chodí až na změny od dalšího běhu). Pak už to jede samo každých 10 min.

### 6. iPhone

Otevři adresu dashboardu v **Safari → Sdílet → Přidat na plochu**.

---

## Když něco nejde

- **Dashboard ukazuje, že centrum neodpovídá:** v **Actions** otevři poslední běh
  a podívej se do logu, u každého centra je ✓ nebo ✗ s chybou. Rezervační
  systémy občas mění svůj web, pak je potřeba upravit `checker/sources.py`.
- **Žádné zprávy:** zkontroluj, že jsi botovi napsal jako první, a pusť *Test Telegramu*.
- **GitHub přestal spouštět kontrolu:** u repozitářů bez aktivity ji po 60 dnech
  vypíná. Tady to nehrozí, protože každý běh ukládá data (a tím je repo aktivní),
  ale kdyby, stačí v Actions kliknout na *Enable workflow*.

## Spuštění u sebe (nepovinné)

```bash
python3 -m checker --dry-run           # vypíše, co našel, nic neposílá
python3 -m checker --only onepadel     # jen jedno centrum
```

Nepotřebuje žádné knihovny, stačí Python 3.10+.

## Jak data čte

| Centrum | Systém | Detail |
|---|---|---|
| OnePadel | CourtyONE | obsazenost po kurtech; ID akcí hledá automaticky v jejich JS |
| Padel Powers | PadelOS | volné sloty po kurtech pro 60/90/120 min |
| Padel Džus | Bookaball | jen „aspoň jeden kurt volný“, proto jeden řádek za centrum |
| Padelmanie | Reservanto | půlhodinová mřížka po kurtech |
| Neride | Sportelo | rezervace po kurtech (GraphQL) |
| Písečná | Playtomic | volné sloty, jen zastřešené kurty 2 a 3 |

**Nepřidané:** Padel Club Spoje (na Playtomicu nenabízí žádné termíny),
SK Slavia Padel (bez přihlášení ukazuje jen dnešek), Sky Sport City (padel jen venku),
Padel Automat Čakovice, Císařská louka a FOR Padel Zdiměřice (dají se doplnit).
