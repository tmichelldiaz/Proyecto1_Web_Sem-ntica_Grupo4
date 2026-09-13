"""
Pruebas de la lógica de parseo/unión, usando archivos de ejemplo pequeños
(sin necesidad de red ni de los datasets reales completos). Correr con:

    pytest -v
"""
import json
import zipfile

import pandas as pd
import requests

from src.utils import add_source, msd_track_id_to_subpath
from src.step2_tagtraum_genre import parse_cls_file
from src.step3_musixmatch_lyrics import parse_mxm_file
from src.step1_musicbrainz_acousticbrainz import extract_mapping_from_lines
from src.step4_lastfm import build_lookup, read_track_json
from src import step5_wikidata
from src.step5_grammy_awards import normalize, match_track, load_grammy_lookup
from src import step5_grammy_awards


def test_msd_track_id_to_subpath():
    assert msd_track_id_to_subpath("TRAAAAW128F429D538") == "A/A/A/TRAAAAW128F429D538.json"
    assert msd_track_id_to_subpath("TRJGUAE12903D0059A") == "J/G/U/TRJGUAE12903D0059A.json"


def test_add_source_appends_only_where_matched():
    fuentes = pd.Series(["MSD", "MSD", "MSD"])
    mask = pd.Series([True, False, True])
    result = add_source(fuentes, mask, "tagtraum")
    assert result == ["MSD;tagtraum", "MSD", "MSD;tagtraum"]


def test_add_source_is_idempotent():
    fuentes = pd.Series(["MSD;tagtraum"])
    mask = pd.Series([True])
    result = add_source(fuentes, mask, "tagtraum")
    assert result == ["MSD;tagtraum"]  # no se duplica


def test_parse_cls_file(tmp_path):
    cls_content = (
        "# comentario de cabecera\n"
        "TRAAAAW128F429D538\tRock\n"
        "TRJGUAE12903D0059A\tElectronic\tDance\n"
    )
    cls_file = tmp_path / "sample.cls"
    cls_file.write_text(cls_content, encoding="utf-8")

    genres = parse_cls_file(cls_file)
    assert genres["TRAAAAW128F429D538"] == "Rock"
    assert genres["TRJGUAE12903D0059A"] == "Electronic;Dance"
    assert len(genres) == 2


def test_parse_mxm_file(tmp_path):
    mxm_content = (
        "#comentario\n"
        "%i,love,you,the,a\n"
        "TRAAAAW128F429D538,MXM001,1:5,2:3,3:1\n"
        "TRJGUAE12903D0059A,MXM002,4:2,5:1\n"
    )
    mxm_file = tmp_path / "mxm_dataset_train.txt"
    mxm_file.write_text(mxm_content, encoding="utf-8")

    lyrics: dict = {}
    parse_mxm_file(mxm_file, None, lyrics)

    assert lyrics["TRAAAAW128F429D538"]["total_words"] == 9  # 5+3+1
    assert lyrics["TRAAAAW128F429D538"]["top_words"] == "i;love;you"  # ordenadas por conteo desc
    assert lyrics["TRJGUAE12903D0059A"]["total_words"] == 3


def test_extract_mapping_from_pretty_json_with_nested_lists(tmp_path):
    # Este es el caso real que rompía el parser viejo: "match" es una lista de
    # LISTAS (no de diccionarios), repartida en varias líneas por el pretty-print.
    lines = json.dumps(
        [
            {
                "query": {"track_id": "TRAAAAW128F429D538", "title": "Song A"},
                "match": [
                    ["1234abcd-1234-abcd-1234-abcd1234abcd", "Song A", []],
                    ["ffffffff-ffff-ffff-ffff-ffffffffffff", "Song A (live)", []],
                ],
            },
            {
                "query": {"track_id": "TRJGUAE12903D0059A", "title": "Song B"},
                "match": [],
            },
        ],
        indent=2,
    ).splitlines(keepends=True)

    mapping, n_tracks = extract_mapping_from_lines(lines)

    assert n_tracks == 2
    assert mapping["TRAAAAW128F429D538"] == "1234abcd-1234-abcd-1234-abcd1234abcd"
    assert "TRJGUAE12903D0059A" not in mapping  # sin match, no debe quedar en el mapeo


def test_extract_mapping_from_compact_json_lines():
    # Variante compacta: un objeto JSON completo por línea (JSON-lines real).
    lines = [
        json.dumps({"track_id": "TRAAAAW128F429D538", "mbid": "1234abcd-1234-abcd-1234-abcd1234abcd"}) + "\n",
        json.dumps({"track_id": "TRJGUAE12903D0059A", "mbid": None}) + "\n",
    ]
    mapping, n_tracks = extract_mapping_from_lines(lines)
    assert n_tracks == 2
    assert mapping == {"TRAAAAW128F429D538": "1234abcd-1234-abcd-1234-abcd1234abcd"}


def test_extract_mapping_handles_entire_file_as_one_giant_line():
    # Este es el caso real que causó el bug: el archivo venía "minificado"
    # (sin saltos de línea), así que read_bz2_text() entrega TODO el
    # contenido como una sola "línea" gigante. Con .search() (versión vieja)
    # solo se habría encontrado la primera canción de las 100.000.
    # 18 caracteres cada uno (TR + 16), igual que un track_id real del MSD
    one_huge_line = (
        "...TRAAAAW128F429D531..."
        "1111aaaa-1111-aaaa-1111-aaaa11112222..."
        "...TRAAAAW128F429D532..."
        "2222bbbb-2222-bbbb-2222-bbbb22223333..."
        "...TRAAAAW128F429D533 sin mbid para esta..."
        "...TRAAAAW128F429D534..."
        "3333cccc-3333-cccc-3333-cccc33334444..."
    )
    mapping, n_tracks = extract_mapping_from_lines([one_huge_line])

    assert n_tracks == 4
    assert mapping["TRAAAAW128F429D531"] == "1111aaaa-1111-aaaa-1111-aaaa11112222"
    assert mapping["TRAAAAW128F429D532"] == "2222bbbb-2222-bbbb-2222-bbbb22223333"
    assert "TRAAAAW128F429D533" not in mapping  # no tenía mbid antes del siguiente track
    assert mapping["TRAAAAW128F429D534"] == "3333cccc-3333-cccc-3333-cccc33334444"


def test_extract_mapping_keeps_first_mbid_seen_per_track():
    lines = [
        "TRAAAAW128F429D538\n",
        "1234abcd-1234-abcd-1234-abcd1234abcd\n",
        "ffffffff-ffff-ffff-ffff-ffffffffffff\n",  # un segundo match: se ignora
    ]
    mapping, _ = extract_mapping_from_lines(lines)
    assert mapping["TRAAAAW128F429D538"] == "1234abcd-1234-abcd-1234-abcd1234abcd"


def test_lastfm_lookup_reads_without_extracting(tmp_path):
    # Simula un .zip de Last.fm real: json anidado en subcarpetas por letra,
    # con un nombre de carpeta raíz arbitrario (aquí "lastfm_train"), tal como
    # viene el archivo real.
    zip_path = tmp_path / "lastfm_train.zip"
    payload = {
        "artist": "Some Artist",
        "title": "Some Song",
        "tags": [["rock", "100"], ["indie", "40"]],
        "similars": [["TRZZZZZ111111111111", "0.9"], ["TRYYYYY222222222222", "0.5"]],
    }
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("lastfm_train/A/A/A/TRAAAAW128F429D538.json", json.dumps(payload))

    with zipfile.ZipFile(zip_path) as zf:
        lookup = build_lookup(zf)
        assert lookup["TRAAAAW128F429D538"] == "lastfm_train/A/A/A/TRAAAAW128F429D538.json"

        data = read_track_json(zf, lookup["TRAAAAW128F429D538"])
        assert data["tags"][0] == ["rock", "100"]
        assert data["similars"][0][0] == "TRZZZZZ111111111111"


def test_lastfm_lookup_missing_track_returns_none(tmp_path):
    zip_path = tmp_path / "lastfm_train.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("lastfm_train/A/A/A/TRAAAAW128F429D538.json", "{}")

    with zipfile.ZipFile(zip_path) as zf:
        lookup = build_lookup(zf)
        assert "TRNOPE0000000000000" not in lookup


def test_query_wikidata_batch_retries_then_succeeds(monkeypatch, tmp_path):
    # Simula 2 fallas transitorias (tipo 502) seguidas de un éxito.
    monkeypatch.setattr(step5_wikidata.config, "WIKIDATA_CACHE_DIR", tmp_path)
    monkeypatch.setattr(step5_wikidata.time, "sleep", lambda s: None)  # no esperar de verdad en el test

    calls = {"n": 0}

    def fake_request_once(mbids):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.HTTPError("502 simulado")
        return [{"mbid": {"value": m}, "artistLabel": {"value": f"Artist-{m}"}} for m in mbids]

    monkeypatch.setattr(step5_wikidata, "_request_once", fake_request_once)

    rows = step5_wikidata.query_wikidata_batch(["mbid-1", "mbid-2"])

    assert calls["n"] == 3  # falló 2 veces, tuvo éxito en el 3er intento
    assert {r["artist_mbid"] for r in rows} == {"mbid-1", "mbid-2"}


def test_query_wikidata_batch_isolates_one_bad_mbid(monkeypatch, tmp_path):
    # Un solo mbid "problemático" hace fallar la consulta siempre; el resto
    # del lote debe recuperarse igual gracias a la partición en mitades.
    monkeypatch.setattr(step5_wikidata.config, "WIKIDATA_CACHE_DIR", tmp_path)
    monkeypatch.setattr(step5_wikidata.time, "sleep", lambda s: None)
    monkeypatch.setattr(step5_wikidata, "MAX_RETRIES", 1)
    monkeypatch.setattr(step5_wikidata, "MIN_BATCH_SIZE", 1)

    def fake_request_once(mbids):
        if "bad-mbid" in mbids:
            raise requests.HTTPError("502 simulado (mbid problemático)")
        return [{"mbid": {"value": m}, "artistLabel": {"value": f"Artist-{m}"}} for m in mbids]

    monkeypatch.setattr(step5_wikidata, "_request_once", fake_request_once)

    mbids = ["good-1", "good-2", "bad-mbid", "good-3", "good-4", "good-5"]
    rows = step5_wikidata.query_wikidata_batch(mbids)

    returned = {r["artist_mbid"] for r in rows}
    assert returned == {"good-1", "good-2", "good-3", "good-4", "good-5"}
    assert "bad-mbid" not in returned


def test_query_wikidata_batch_504_splits_immediately_without_wasting_retries(monkeypatch, tmp_path):
    # Un 504 significa "la consulta tardó demasiado" -- reintentar EXACTAMENTE
    # la misma consulta del mismo tamaño no debería intentarse 3 veces (eso
    # solo desperdicia minutos); debe partirse en mitades de una vez.
    monkeypatch.setattr(step5_wikidata.config, "WIKIDATA_CACHE_DIR", tmp_path)
    monkeypatch.setattr(step5_wikidata.time, "sleep", lambda s: None)
    monkeypatch.setattr(step5_wikidata, "MIN_BATCH_SIZE", 1)

    calls_per_size = []

    def fake_request_once(mbids):
        calls_per_size.append(len(mbids))
        if len(mbids) > 2:
            raise step5_wikidata._RetryableWikidataError(504, "504 simulado (timeout)")
        return [{"mbid": {"value": m}, "artistLabel": {"value": f"Artist-{m}"}} for m in mbids]

    monkeypatch.setattr(step5_wikidata, "_request_once", fake_request_once)

    rows = step5_wikidata.query_wikidata_batch(["a", "b", "c", "d"])

    # el lote de 4 debió intentarse UNA sola vez (no las 3 de MAX_RETRIES) antes de partirse
    assert calls_per_size.count(4) == 1
    assert {r["artist_mbid"] for r in rows} == {"a", "b", "c", "d"}


def test_grammy_normalize_strips_accents_punctuation_and_parens():
    assert normalize("Bohemian Rhapsody (Remastered 2011)") == "bohemian rhapsody"
    assert normalize("Despacito (feat. Justin Bieber)") == "despacito"
    assert normalize("Canción") == "cancion"
    assert normalize(None) == ""


def test_grammy_match_track_by_title_and_partial_artist():
    lookup = {
        "thriller": [
            {"year": "1984", "category": "Album of the Year", "artist_raw": "Michael Jackson",
             "artist_norm": normalize("Michael Jackson"), "winner": True},
        ]
    }
    matches = match_track(normalize("Thriller"), normalize("Michael Jackson"), lookup)
    assert len(matches) == 1
    assert matches[0]["winner"] is True

    # artista distinto con el mismo título: no debe machear
    no_match = match_track(normalize("Thriller"), normalize("Otro Artista"), lookup)
    assert no_match == []


def test_grammy_match_track_no_candidates_returns_empty():
    assert match_track(normalize("Cancion Que No Existe"), normalize("Nadie"), {}) == []


def test_load_grammy_lookup_real_header_assumes_all_winners(monkeypatch, tmp_path):
    # Formato real de grammysTo2014.csv: Year,Category,Title,Winners -- sin
    # columna booleana de ganador por separado.
    csv_path = tmp_path / "grammysTo2014.csv"
    csv_path.write_text(
        "Year,Category,Title,Winners\n"
        '2013,Record Of The Year,Get Lucky,"Daft Punk (Thomas Bangalter & Guy-Manuel de Homem-Christo), artists."\n'
        '2013,Best New Artist,,"Macklemore & Ryan Lewis, artists."\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(step5_grammy_awards.config, "GRAMMY_CSV", csv_path)
    monkeypatch.setattr(step5_grammy_awards, "safe_download", lambda *a, **k: True)

    lookup = load_grammy_lookup()

    assert "get lucky" in lookup
    entry = lookup["get lucky"][0]
    assert entry["winner"] is True  # se asume ganador al no haber columna de ganador
    assert entry["year"] == "2013"
    assert "daft punk" in entry["artist_norm"]

    # la fila con título vacío ("Best New Artist") no debe quedar indexada
    assert "" not in lookup
