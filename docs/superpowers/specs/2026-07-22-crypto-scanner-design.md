# Crypto Scanner — Dizajn dokument

**Datum:** 2026-07-22
**Status:** Odobren dizajn, ceka plan implementacije

## Cilj

Alat koji istrazuje i pronalazi jeftine crypto coine (Solana memecoini + niske-cap
altcoini) sa kratkorocnim potencijalom i prikazuje **top 10** na javnom sajtu.
Namenjen brzoj kupovini-prodaji (kratko drzanje), sa malim ulogom i niskim
ocekivanjima od profita. Memecoini su prihvatljivi, ali ocigledan scam se izbacuje.

**Vazna napomena:** Alat prikuplja i prikazuje podatke i signale. Nije investicioni
savet i ne izvrsava kupovinu/prodaju. Odluka je uvek na korisniku.

## Arhitektura (velika slika)

```
TVOJ KOMPJUTER                          OBLAK (besplatno)
┌─────────────────────────┐            ┌──────────────────┐
│  Python skripta         │  git push  │  GitHub repo     │
│  (radi svakih 15 min)   │ ─────────► │  data branch:    │
│  - povlaci podatke      │  data.json │  data.json       │
│  - proverava rugcheck   │            └────────┬─────────┘
│  - rangira → top 10     │                     │ fetch (raw)
│  - upisuje data.json    │            ┌────────▼─────────┐
└─────────────────────────┘            │  Vercel sajt     │
                                        │  (statican)      │
                                        │  prikazuje 10    │
                                        │  osvezava se sam │
                                        └──────────────────┘
```

- Skripta i podaci zive lokalno na korisnikovom kompjuteru.
- Podaci se objavljuju gurањem `data.json` na poseban `data` branch na GitHub-u.
- Vercel sajt je statican; cita JSON direktno sa GitHub-a (raw) i osvezava se sam.
- Kad je kompjuter ugasen, sajt prikazuje poslednje podatke uz "azurirano pre X min".

**Odabrani pristup za transport podataka:** GitHub kao skladiste (Pristup A) —
najmanje pokretnih delova, besplatno, nista osetljivo ne izlazi iz kompjutera,
istorija snapshotova dolazi besplatno (koristi se za Fazu 2 / ML).

## Izvori podataka (svi besplatni, bez kljuca gde god moze)

- **DexScreener API** — glavni izvor. Cena, promena cene (5min/1h/6h/24h), volumen,
  likvidnost, vreme kreiranja para (svezina). Solana + EVM lanci. Bez kljuca.
- **RugCheck API** (rugcheck.xyz) — samo Solana: rizik skor, zakljucanost likvidnosti,
  koncentracija holdera. Bez kljuca. Koristi solana-rugcheck-skill.
- **CoinGecko free API** — opciono, siri kontekst niske-cap altcoina (market cap).
  Koristi se stedljivo zbog limita.

## Komponente skripte

Mali, jasni moduli — svaki radi jednu stvar:

```
fetch_dex.py      → povlaci kandidate sa DexScreener-a
fetch_rugcheck.py → proverava bezbednost Solana tokena
score.py          → racuna skor i bira top 10
build_data.py     → sklapa data.json (uvek validan format)
publish.py        → git push na data branch
main.py           → orkestrira sve, petlja na 15 min
config.py         → podesavanja (tezine, filteri, pragovi)
```

**Tok jednog ciklusa:** povuci ~100–200 kandidata sa DexScreener-a (filter: min
likvidnost/volumen) → za Solana tokene pusti rugcheck → izbaci scam (tvrdi filter)
→ izracunaj skor → uzmi top 10 → napravi `data.json` → gurni na GitHub. Ponovi za 15 min.

## Sistem bodovanja

Svaki coin dobija skor 0–100 kao ponderisani zbir cetiri signala (svaki normalizovan 0–100):

| Signal | Tezina | Sta meri |
|---|---|---|
| Momentum | 35% | Rast cene + skok volumena (5min/1h/24h) |
| Likvidnost/volumen | 30% | Moguce lako uci/izaci; nisko = izbacen |
| Bezbednost (rugcheck) | 20% | Solana: rugcheck; ostali: proxy (starost LP, koncentracija) |
| Svezina | 15% | Mladji tokeni sa rastucom paznjom, ne prestari |

**Dva sloja zastite:**
1. **Tvrdi filteri (pre bodovanja):** izbaci ako likvidnost < prag, volumen premali,
   ili rugcheck = visok rizik/"danger".
2. **Bodovanje:** ono sto prodje filtere se rangira, top 10 ide na sajt.

Sve tezine i pragovi su u `config.py`. Sajt prikazuje razbijen skor po komponentama +
rizik oznaku, da korisnik vidi zasto je coin tu. Momentum + likvidnost zajedno nose
65% jer je alat naStelovan za "udji u nesto sto se krece i moze da se proda", ne za
dugorocno drzanje.

## Sajt (statican, Vercel)

Obican HTML/CSS/JS. Cita `data.json` sa GitHub-a, osvezava se sam na 15 min.

- **Zaglavlje:** naslov + "Azurirano pre X min" (zeleno <20min, zuto starije).
- **Top 10 kartica**, svaka: rang, ime/simbol, lanac, cena; promena 5min/1h/24h
  (zeleno/crveno); ukupan skor + razbijen prikaz; rizik oznaka 🟢/🟡/🔴; likvidnost i
  volumen 24h; dugmici na DexScreener (grafikon) i RugCheck (bezbednost).
- **Diskrejmer** u podnozju: "Nije investicioni savet. Kripto je visokorizican."
- **Dizajn:** cist taman trading izgled, citljiv na telefonu. Koristi interface-design skill.
- **Kad podaci fale:** prikazi poslednje + poruku "ne mogu da dohvatim sveze podatke".
  Nikad prazan ekran.

## Rukovanje greskama (skripta)

- API pad/timeout → preskoci izvor, koristi ostale, kratki retry. Jedan pad ne obara ciklus.
- Rugcheck bez odgovora → token = "nepoznat rizik" (🟡), ne "siguran".
- Ceo ciklus padne → uloguj gresku, zadrzi poslednji dobar `data.json`, cekaj 15 min, pokusaj opet.
- Rate-limit → automatsko usporavanje/pauza.
- Sve u lokalni log fajl.

## Testiranje

- `score.py` — testovi bodovanja (scam prolazi filter? momentum rangira tacno?). TDD.
- Parsiranje API odgovora — testovi sa sacuvanim primerima odgovora.
- `build_data.py` — validacija formata pre gurања.

## Faza 2 (opciono, kasnije): ML

Pravila rade sada. Pošto svaki snapshot ide na GitHub, sami skupljamo dataset
(coin u trenutku T → sta se desilo posle 1h/24h). Kad se nakupi par nedelja podataka,
moze da se istrenira jednostavan model (npr. gradient boosting) da predvidja verovatnocu
skoka i uporedi sa pravilima; ako je bolji, ubacuje se kao dodatni signal. ML nije
magican i ne menja niska ocekivanja od profita.

## Odluke odlozene za kasnije

- Podesavanje GitHub repoa i Vercel deploy-a (korisnik ce srediti naknadno).
- Tacan `git init` / commit ovog spec-a — git jos nije inicijalizovan u folderu.
