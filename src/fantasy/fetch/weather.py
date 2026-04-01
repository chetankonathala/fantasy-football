"""Open-Meteo weather client — fetches wind and precipitation for outdoor NFL games."""
import logging

import requests

log = logging.getLogger(__name__)

DOME_TEAMS: frozenset[str] = frozenset({
    "ARI", "ATL", "DAL", "DET", "HOU", "IND", "LV", "LAR", "LAC", "MIN", "NO",
})

STADIUM_COORDS: dict[str, tuple[float, float]] = {
    "BUF": (42.77, -78.79),
    "NE": (42.09, -71.26),
    "MIA": (25.96, -80.24),
    "NYJ": (40.81, -74.07),
    "NYG": (40.81, -74.07),
    "BAL": (39.28, -76.62),
    "CIN": (39.10, -84.52),
    "CLE": (41.50, -81.70),
    "PIT": (40.45, -80.02),
    "HOU": (29.68, -95.41),
    "IND": (39.76, -86.16),
    "JAX": (30.32, -81.64),
    "TEN": (36.17, -86.77),
    "DEN": (39.74, -105.02),
    "KC": (39.05, -94.48),
    "LV": (36.09, -115.18),
    "LAC": (33.95, -118.34),
    "LAR": (33.95, -118.34),
    "DAL": (32.75, -97.09),
    "PHI": (39.90, -75.17),
    "WAS": (38.91, -76.86),
    "CHI": (41.86, -87.62),
    "DET": (42.34, -83.04),
    "GB": (44.50, -88.06),
    "MIN": (44.97, -93.26),
    "ATL": (33.75, -84.40),
    "CAR": (35.23, -80.85),
    "NO": (29.95, -90.08),
    "TB": (27.98, -82.50),
    "ARI": (33.53, -112.26),
    "SF": (37.40, -121.97),
    "SEA": (47.60, -122.33),
}

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WIND_THRESHOLD_MPH = 15
PRECIP_THRESHOLD_PCT = 30


def fetch_weather(game_lines: list[dict]) -> list[dict]:
    """Enrich game_line dicts with weather data.

    For dome teams: sets is_dome=True, weather_flag=False, wind/precip=None.
    For outdoor teams: fetches from Open-Meteo using home stadium coords.

    Args:
        game_lines: list of dicts with at least 'home_team' and 'game_date' keys

    Returns:
        The same dicts updated in-place with is_dome, wind_mph, precip_probability, weather_flag.
    """
    for gl in game_lines:
        home = gl.get("home_team", "")

        if home in DOME_TEAMS:
            gl["is_dome"] = True
            gl["wind_mph"] = None
            gl["precip_probability"] = None
            gl["weather_flag"] = False
            continue

        gl["is_dome"] = False
        coords = STADIUM_COORDS.get(home)
        if not coords:
            log.warning("No coordinates for home team %s — skipping weather", home)
            gl["wind_mph"] = None
            gl["precip_probability"] = None
            gl["weather_flag"] = False
            continue

        lat, lon = coords
        try:
            resp = requests.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "wind_speed_10m,precipitation_probability",
                    "wind_speed_unit": "mph",
                    "timezone": "America/Chicago",
                    "forecast_days": 7,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            # Find the hour closest to 1pm (typical kickoff) on game_date
            game_date = gl.get("game_date", "")
            target_hour = f"{game_date}T13:00"
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            winds = hourly.get("wind_speed_10m", [])
            precips = hourly.get("precipitation_probability", [])

            wind_mph = None
            precip_prob = None
            for i, t in enumerate(times):
                if t.startswith(target_hour[:13]):  # match YYYY-MM-DDTHH
                    wind_mph = winds[i] if i < len(winds) else None
                    precip_prob = precips[i] if i < len(precips) else None
                    break

            gl["wind_mph"] = wind_mph
            gl["precip_probability"] = precip_prob
            gl["weather_flag"] = (
                (wind_mph is not None and wind_mph > WIND_THRESHOLD_MPH)
                or (precip_prob is not None and precip_prob > PRECIP_THRESHOLD_PCT)
            )

        except requests.RequestException as exc:
            log.error("Weather fetch failed for %s: %s", home, exc)
            gl["wind_mph"] = None
            gl["precip_probability"] = None
            gl["weather_flag"] = False

    return game_lines
