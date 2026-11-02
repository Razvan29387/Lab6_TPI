from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Tpi IoT API")

# Regex: doar litere mici a-z, cifre 0-9, cratimă, lungime 1-32
app.DEV_PATTERN = r"^[a-z0-9\-]{1,32}$"


class Reading(BaseModel):
    # Verifică dacă textul are doar a-z, 0-9 și cratimă, cu o lungime între 1 și 32 caractere
    dev: str = Field(pattern=app.DEV_PATTERN)

    # Verifică dacă numărul de ordine (seq) este un număr întreg mai mare sau egal cu 0
    seq: int = Field(ge=0)

    # Verifică dacă timestamp-ul este mai mare de 1.600.000.000 (după sept. 2020), eliminând citirile cu ceas nesetat
    ts: int = Field(gt=1_600_000_000)

    # Verifică dacă temperatura înregistrată este în limite fizice plauzibile: între -40 și 85 °C
    temp: float = Field(ge=-40, le=85)

    # Verifică dacă umiditatea, dacă este trimisă, se încadrează între 0 și 100%. Este un câmp opțional (null/None)
    hum: float | None = Field(default=None, ge=0, le=100)


# Baza de date în memorie (dicționar de dicționare)
DB: dict[str, dict[int, Reading]] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


# === 2. POST /readings ===
@app.post("/readings", status_code=201)
def add_reading(reading: Reading):
    if reading.dev not in DB:
        DB[reading.dev] = {}

    if reading.seq in DB[reading.dev]:
        raise HTTPException(status_code=409, detail="O citire cu acest 'seq' exista deja pentru acest dispozitiv.")

    DB[reading.dev][reading.seq] = reading
    return reading


# === 3. GET /devices/{dev_id}/readings ===
@app.get("/devices/{dev_id}/readings")
def readings(
        dev_id: str = Path(..., pattern=app.DEV_PATTERN),
        since: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=100),
        min_temp: float | None = Query(None, description="[BONUS] Filtrează temp >= min_temp")
) -> list[Reading]:
    # 404 dacă dispozitivul nu are nicio citire
    if dev_id not in DB or not DB[dev_id]:
        raise HTTPException(status_code=404, detail="Dispozitivul nu are citiri salvate.")

    # Extragem și filtrăm
    device_readings = DB[dev_id].values()
    filtered = [r for r in device_readings if r.seq > since]

    # [BONUS] Aplicare min_temp
    if min_temp is not None:
        filtered = [r for r in filtered if r.temp >= min_temp]

    # Ordonare și aplicarea limitei
    filtered.sort(key=lambda r: r.seq)
    return filtered[:limit]


# === [BONUS] GET /devices ===
@app.get("/devices")
def get_devices():
    """
    Returnează lista dispozitivelor și numărul de citiri al fiecăruia.
    """
    return [{"dev": dev, "total_readings": len(reads)} for dev, reads in DB.items()]