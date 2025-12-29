#!/usr/bin/env python3
"""Movie showtime viewer using Textual."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from .cache import Cache
from .config import Config, Theater


class MovieTable(Static, can_focus=True):
    """Widget to display a movie with a table of showtimes."""

    DEFAULT_CSS = """
    MovieTable {
        margin: 1 0 2 0;
        height: auto;
        border: solid transparent;
    }

    MovieTable:focus {
        border: solid $accent;
    }

    MovieTable .movie-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    MovieTable DataTable {
        height: auto;
    }
    """

    def __init__(
        self,
        movie_name: str,
        duration: int,
        showtimes_by_date: dict[str, list[dict[str, Any]]],
        movie_data: dict[str, Any],
    ) -> None:
        super().__init__()
        self.movie_name = movie_name
        self.duration = duration
        self.showtimes_by_date = showtimes_by_date
        self.movie_data = movie_data

    def compose(self) -> ComposeResult:
        yield Label(f"{self.movie_name} ({self.duration} min)", classes="movie-header")

        table = DataTable(show_cursor=False, zebra_stripes=True)

        sorted_dates = sorted(self.showtimes_by_date.keys())
        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]

        columns = ["Time"] + [d.strftime("%a %m/%d") for d in date_objects]
        for col in columns:
            table.add_column(col, key=col)

        times_set: set[str] = set()
        for showtimes in self.showtimes_by_date.values():
            for show in showtimes:
                times_set.add(show["time"])

        sorted_times = sorted(list(times_set))

        for time in sorted_times:
            row_data = [time]

            for date_str in sorted_dates:
                showtimes = self.showtimes_by_date.get(date_str, [])
                matching_shows = [s for s in showtimes if s["time"] == time]

                if matching_shows:
                    show = matching_shows[0]
                    flags_text = ""
                    if show["flags"]:
                        flag_codes = [f["code"] for f in show["flags"]]
                        flags_text = f" ({', '.join(flag_codes)})"
                    row_data.append("✓" + flags_text)
                else:
                    row_data.append("")

            table.add_row(*row_data)

        yield table

    async def on_click(self) -> None:
        """Handle click on movie table."""
        self.app.push_screen(MovieDetailModal(self.movie_data))

    def on_key(self, event: events.Key) -> None:
        """Handle key press on movie table."""
        if event.key == "enter":
            self.app.push_screen(MovieDetailModal(self.movie_data))
            event.stop()


class MovieDetailModal(ModalScreen[None]):
    """Modal screen to display movie details."""

    DEFAULT_CSS = """
    MovieDetailModal {
        align: center middle;
    }

    #detail-dialog {
        padding: 2 4;
        width: 90;
        height: 80%;
        border: thick $accent;
        background: $surface;
        layout: grid;
        grid-size: 1 3;
        grid-rows: auto 1fr auto;
    }

    #detail-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }

    #detail-scroll {
        width: 100%;
        overflow-y: auto;
    }

    #detail-content {
        width: 100%;
        height: auto;
    }

    #detail-close {
        width: 100%;
        height: auto;
        min-height: 4;
        margin-top: 1;
    }
    """

    def __init__(self, movie_data: dict[str, Any]) -> None:
        super().__init__()
        self.movie_data = movie_data

    def compose(self) -> ComposeResult:
        with Container(id="detail-dialog"):
            movie_details = self.movie_data.get("details", {})

            title = self.movie_data["name"]
            if (
                movie_details.get("title_orig")
                and movie_details.get("title_orig") != title
            ):
                title = f"{title} ({movie_details['title_orig']})"
            yield Label(title, id="detail-title")

            details: list[str] = []

            if movie_details.get("short_description"):
                details.append(movie_details["short_description"])
                details.append("")

            if movie_details.get("description"):
                details.append(movie_details["description"])
                details.append("")

            info_parts = []
            if movie_details.get("productionYear"):
                info_parts.append(str(movie_details["productionYear"]))
            if movie_details.get("productionCountries"):
                countries = ", ".join(movie_details["productionCountries"][:2])
                info_parts.append(countries)
            if info_parts:
                details.append(" | ".join(info_parts))

            details.append(f"Duration: {self.movie_data['duration']} minutes")

            if movie_details.get("ageClassificationRating"):
                rating = movie_details["ageClassificationRating"]
                details.append(
                    f"Rating: {rating.get('type', '')} {rating.get('value', '')}"
                )

            if movie_details.get("genres"):
                genres = ", ".join([g["name"] for g in movie_details["genres"]])
                details.append(f"Genres: {genres}")

            released = movie_details.get("released") or self.movie_data.get("released")
            if released:
                details.append(f"Released: {released[:10]}")

            if movie_details.get("directors"):
                directors = ", ".join([d["name"] for d in movie_details["directors"]])
                details.append(f"Director: {directors}")

            if movie_details.get("actors"):
                actors = ", ".join([a["name"] for a in movie_details["actors"][:4]])
                if len(movie_details["actors"]) > 4:
                    actors += ", ..."
                details.append(f"Cast: {actors}")

            if movie_details.get("trailers"):
                trailers = movie_details["trailers"]
                if trailers:
                    details.append("\nTrailers:")
                    for trailer in trailers:
                        trailer_url = trailer.get("url", "")
                        trailer_format = trailer.get("format", "").upper()
                        if trailer_url:
                            details.append(f"  • {trailer_format}: {trailer_url}")

            details.append(f"\nTotal Showtimes: {self.movie_data['total_showtimes']}")

            all_flags = set()
            for showtimes in self.movie_data["showtimes_by_date"].values():
                for show in showtimes:
                    for flag in show.get("flags", []):
                        all_flags.add(f"{flag['name']} ({flag['code']})")

            if all_flags:
                details.append("Special Showings:")
                for flag in sorted(all_flags):
                    details.append(f"  • {flag}")

            dates = sorted(self.movie_data["showtimes_by_date"].keys())
            if dates:
                date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
                details.append(
                    f"\nShowing: {date_objs[0].strftime('%a %m/%d')} to {date_objs[-1].strftime('%a %m/%d')}"
                )

            with VerticalScroll(id="detail-scroll"):
                yield Static("\n".join(details), id="detail-content")
            yield Button("Back", variant="primary", id="detail-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button."""
        self.dismiss()

    def on_key(self, event: events.Key) -> None:
        """Handle escape key."""
        if event.key == "escape":
            self.dismiss()
            event.stop()


class TheaterHeader(Static):
    """Widget to display theater name as a section header."""

    DEFAULT_CSS = """
    TheaterHeader {
        width: 100%;
        height: auto;
        margin: 2 0 1 0;
        padding: 1 2;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, theater_name: str) -> None:
        super().__init__(theater_name)


class SearchCityModal(ModalScreen[str | None]):
    """Modal screen to search for theaters by city."""

    DEFAULT_CSS = """
    SearchCityModal {
        align: center middle;
    }

    #search-dialog {
        padding: 2 4;
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
    }

    #search-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }

    #search-input {
        margin: 1 0;
        width: 100%;
    }

    #search-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    #search-buttons Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="search-dialog"):
            yield Label("Search for Theaters", id="search-title")
            yield Label("Enter city name:")
            yield Input(placeholder="e.g., Tübingen, Berlin", id="search-input")
            with Container(id="search-buttons"):
                yield Button("Search", variant="primary", id="search-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        """Focus the input when the modal opens."""
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "search-btn":
            city_input = self.query_one("#search-input", Input)
            city = city_input.value.strip()
            if city:
                self.dismiss(city)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "enter":
            city_input = self.query_one("#search-input", Input)
            city = city_input.value.strip()
            if city:
                self.dismiss(city)
            event.stop()


class TheaterResultsModal(ModalScreen[None]):
    """Modal screen to display search results."""

    DEFAULT_CSS = """
    TheaterResultsModal {
        align: center middle;
    }

    #results-dialog {
        padding: 2 4;
        width: 90;
        height: 80%;
        border: thick $accent;
        background: $surface;
        layout: grid;
        grid-size: 1 3;
        grid-rows: auto 1fr auto;
    }

    #results-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }

    #results-scroll {
        width: 100%;
        overflow-y: auto;
    }

    #results-content {
        width: 100%;
        height: auto;
    }

    #results-close {
        width: 100%;
        height: auto;
        min-height: 4;
        margin-top: 1;
    }
    """

    def __init__(self, results: list[dict[str, Any]], city: str) -> None:
        super().__init__()
        self.results = results
        self.city = city

    def compose(self) -> ComposeResult:
        with Container(id="results-dialog"):
            yield Label(f"Theater Search Results for '{self.city}'", id="results-title")

            if not self.results:
                with VerticalScroll(id="results-scroll"):
                    yield Label("No theaters found.", id="results-content")
            else:
                content_lines = []
                content_lines.append(f"Found {len(self.results)} theater(s):\n")

                for result in self.results:
                    result_type = result.get("__typename", "")

                    if result_type == "Cinema":
                        name = result.get("name", "Unknown")
                        cinema_id = result.get("id", "N/A")
                        street = result.get("street", "")
                        postcode = result.get("postcode", {}).get("postcode", "")
                        city_info = result.get("city", {})
                        city_name = city_info.get("name", "")

                        content_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        content_lines.append(f"Name: {name}")
                        content_lines.append(f"Cinema ID: {cinema_id}")
                        if street:
                            content_lines.append(f"Address: {street}")
                        if postcode or city_name:
                            content_lines.append(
                                f"Location: {postcode} {city_name}".strip()
                            )

                        is_open_air = result.get("isOpenAir", False)
                        is_drive_in = result.get("isDriveIn", False)
                        if is_open_air:
                            content_lines.append("Type: Open Air")
                        if is_drive_in:
                            content_lines.append("Type: Drive-In")

                        content_lines.append("")

                    elif result_type == "City":
                        city_name = result.get("name", "Unknown")
                        city_id = result.get("id", "N/A")
                        postcodes = result.get("postcodes", [])
                        postcode_list = ", ".join(
                            [p.get("postcode", "") for p in postcodes[:3]]
                        )

                        content_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        content_lines.append(f"City: {city_name}")
                        content_lines.append(f"City ID: {city_id}")
                        if postcode_list:
                            content_lines.append(f"Postcodes: {postcode_list}")
                        content_lines.append("")

                with VerticalScroll(id="results-scroll"):
                    yield Static("\n".join(content_lines), id="results-content")

            yield Button("Back", variant="primary", id="results-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button."""
        self.dismiss()

    def on_key(self, event: events.Key) -> None:
        """Handle escape key."""
        if event.key == "escape":
            self.dismiss()
            event.stop()


class MovieShowtimesApp(App[None]):
    """Textual app to display movie showtimes."""

    CSS = """
    Screen {
        align: center top;
    }

    VerticalScroll {
        height: 100%;
        width: 100%;
    }

    #content {
        width: 100%;
        height: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "toggle_sort", "Toggle Sort"),
        ("g", "toggle_grouping", "Toggle Grouping"),
        ("f", "search_theaters", "Search Theaters"),
    ]

    def __init__(self) -> None:
        self.config = Config.load()
        self.theaters = self.config.theaters
        self.cache = Cache()
        super().__init__()
        self.title = "Kinostar - Showtimes"
        self.theaters_data: dict[str, dict[str, Any]] = {}
        self.sort_by_release = False
        self.group_by_theater = True

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="content"):
            yield Label("Loading showtimes...", id="loading")
        yield Footer()

    async def on_mount(self) -> None:
        """Load data when the app starts."""
        await self.load_showtimes()
        self.refresh_ui()

    async def load_showtimes_for_theater(
        self, client: httpx.AsyncClient, theater: Theater
    ) -> tuple[Theater, dict[str, Any]]:
        """Fetch showtimes for a single theater."""
        cached_data = self.cache.get("showtimes", theater.cinema_id)
        if cached_data is not None:
            return theater, cached_data

        url = "https://www.kinoheld.de/ajax/getShowsForCinemas"
        params = {"cinemaIds[]": str(theater.cinema_id), "lang": "de"}
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.7,de-DE;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://www.kinoheld.de/cinema/tuebingen/kino-museum-tuebingen/shows/movies?appView=1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "TE": "trailers",
        }

        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.cache.set("showtimes", data, theater.cinema_id)
            return theater, data
        except Exception as e:
            error_data = {"shows": [], "error": str(e), "movies": {}}
            return theater, error_data

    async def load_showtimes(self) -> None:
        """Fetch showtimes from the API for all theaters."""
        async with httpx.AsyncClient() as client:
            tasks = [
                self.load_showtimes_for_theater(client, theater)
                for theater in self.theaters
            ]
            results = await asyncio.gather(*tasks)

            for theater, data in results:
                self.theaters_data[theater.name] = {
                    "theater": theater,
                    "shows_data": data,
                    "movies_data": data.get("movies", {}),
                }

    def _process_theater_shows(
        self,
        theater: Theater,
        shows_data: dict[str, Any],
        movies_data: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Process shows for a theater and return movies dict."""
        if not shows_data or "shows" not in shows_data:
            return {}

        shows = shows_data["shows"]
        if not shows:
            return {}

        movies: dict[str, dict[str, Any]] = {}
        for show in shows:
            movie_name = show["name"]

            if self.config.should_filter_movie(movie_name, theater):
                continue

            if movie_name not in movies:
                movie_id = str(show.get("movieId", ""))
                movie_details = movies_data.get(movie_id, {})
                released = movie_details.get("released") or show.get("released") or ""
                movies[movie_name] = {
                    "name": movie_name,
                    "duration": show["duration"],
                    "showtimes_by_date": defaultdict(list),
                    "total_showtimes": 0,
                    "released": released,
                    "movieId": movie_id,
                    "details": movie_details,
                }
            movies[movie_name]["showtimes_by_date"][show["date"]].append(show)
            movies[movie_name]["total_showtimes"] += 1

        return movies

    def refresh_ui(self) -> None:
        """Refresh the UI with current sort order."""
        scroll_container = self.query_one("#content", VerticalScroll)

        try:
            loading_label = scroll_container.query_one("#loading", Label)
            loading_label.remove()
        except Exception:
            scroll_container.remove_children()

        if not self.theaters_data:
            scroll_container.mount(Label("No theaters configured."))
            return

        if self.group_by_theater:
            self._render_by_theater(scroll_container)
        else:
            self._render_by_movie(scroll_container)

    def _render_by_theater(self, scroll_container: VerticalScroll) -> None:
        """Render UI grouped by theater."""
        first_table = None

        for theater_name, theater_info in self.theaters_data.items():
            theater = theater_info["theater"]
            shows_data = theater_info["shows_data"]
            movies_data = theater_info["movies_data"]

            scroll_container.mount(TheaterHeader(theater_name))

            if not shows_data or "shows" not in shows_data:
                error_msg = "No showtimes available."
                if shows_data and "error" in shows_data:
                    error_msg += f"\nError: {shows_data['error']}"
                scroll_container.mount(Label(error_msg))
                continue

            movies = self._process_theater_shows(theater, shows_data, movies_data)

            if not movies:
                scroll_container.mount(Label("No showtimes available."))
                continue

            if self.sort_by_release:
                sorted_movies = sorted(
                    movies.items(),
                    key=lambda x: x[1]["released"] or "",
                    reverse=True,
                )
            else:
                sorted_movies = sorted(
                    movies.items(), key=lambda x: x[1]["total_showtimes"], reverse=True
                )

            for movie_name, movie_data in sorted_movies:
                table = MovieTable(
                    movie_name,
                    movie_data["duration"],
                    dict(movie_data["showtimes_by_date"]),
                    movie_data,
                )
                scroll_container.mount(table)
                if first_table is None:
                    first_table = table

        if first_table is not None:
            self.set_focus(first_table)

    def _render_by_movie(self, scroll_container: VerticalScroll) -> None:
        """Render UI grouped by movie."""
        # Collect all movies across all theaters
        all_movies: dict[str, list[tuple[str, Theater, dict[str, Any]]]] = defaultdict(
            list
        )

        for theater_name, theater_info in self.theaters_data.items():
            theater = theater_info["theater"]
            shows_data = theater_info["shows_data"]
            movies_data = theater_info["movies_data"]

            movies = self._process_theater_shows(theater, shows_data, movies_data)

            for movie_name, movie_data in movies.items():
                all_movies[movie_name].append((theater_name, theater, movie_data))

        if not all_movies:
            scroll_container.mount(Label("No showtimes available."))
            return

        # Sort movies
        if self.sort_by_release:
            sorted_movie_names = sorted(
                all_movies.keys(),
                key=lambda name: max(
                    (data[2]["released"] or "" for data in all_movies[name]), default=""
                ),
                reverse=True,
            )
        else:
            sorted_movie_names = sorted(
                all_movies.keys(),
                key=lambda name: sum(
                    data[2]["total_showtimes"] for data in all_movies[name]
                ),
                reverse=True,
            )

        first_table = None

        for movie_name in sorted_movie_names:
            theaters_for_movie = all_movies[movie_name]

            # Sort theaters alphabetically for consistent display
            theaters_for_movie.sort(key=lambda x: x[0])

            for theater_name, theater, movie_data in theaters_for_movie:
                display_name = f"{movie_name} [{theater_name}]"
                table = MovieTable(
                    display_name,
                    movie_data["duration"],
                    dict(movie_data["showtimes_by_date"]),
                    movie_data,
                )
                scroll_container.mount(table)
                if first_table is None:
                    first_table = table

        if first_table is not None:
            self.set_focus(first_table)

    def action_toggle_sort(self) -> None:
        """Toggle between sorting by showtimes and release date."""
        self.sort_by_release = not self.sort_by_release
        self.refresh_ui()

    def action_toggle_grouping(self) -> None:
        """Toggle between grouping by theater and grouping by movie."""
        self.group_by_theater = not self.group_by_theater
        self.refresh_ui()

    async def search_theaters_by_city(self, city: str) -> list[dict[str, Any]]:
        """Search for theaters using the Kinoheld GraphQL API."""
        cached_results = self.cache.get("theater_search", city.lower())
        if cached_results is not None:
            return cached_results

        url = "https://next-live.kinoheld.de/graphql"

        graphql_query = """
    query FetchSearchForAutoSuggest($query: String, $limit: Int! = 25, $types: [SearchTypeEnum!]) {
  search(query: $query, limit: $limit, types: $types) {
    __typename
    ... on Movie {
      id
      title
      urlSlug
      duration
      released
      genres {
        ...GenreAttributes
      }
      thumbnailImage {
        ...ImageAttributes
      }
    }
    ... on Person {
      name
      urlSlug
      profileImage {
        ...ImageAttributes
      }
      actedIn {
        paginatorInfo {
          total
        }
      }
      directedIn {
        paginatorInfo {
          total
        }
      }
    }
    ... on City {
      id
      ...CityAttributes
      postcodes {
        postcode
      }
    }
    ... on Cinema {
      id
      name
      urlSlug
      street
      isOpenAir
      isDriveIn
      isStationary
      postcode {
        postcode
      }
      city {
        id
        urlSlug
        name
      }
      thumbnailImage {
        ...ImageAttributes
      }
    }
  }
}

    fragment GenreAttributes on Genre {
  id
  name
  urlSlug
}


    fragment ImageAttributes on Image {
  id
  url
  colors(limit: 3)
  width
  height
}


    fragment CityAttributes on City {
  id
  distance
  latitude
  urlSlug
  longitude
  name
  timezone
}
    """

        variables = {"query": city, "limit": 25, "types": ["CINEMA", "CITY"]}

        payload = {
            "query": graphql_query,
            "variables": variables,
            "operationName": "FetchSearchForAutoSuggest",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.6925.99 Safari/537.36 Edg/133.0.3350.106",
            "Accept": "application/graphql-response+json, application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://www.kinoheld.de/",
            "Content-Type": "application/json",
            "Origin": "https://www.kinoheld.de",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                results = data.get("data", {}).get("search", [])
                self.cache.set("theater_search", results, city.lower())
                return results
            except Exception as e:
                error_results = [{"error": str(e)}]
                return error_results

    def action_search_theaters(self) -> None:
        """Open the search modal to find theaters by city."""

        async def handle_search(city: str | None) -> None:
            if city:
                results = await self.search_theaters_by_city(city)
                self.push_screen(TheaterResultsModal(results, city))

        self.push_screen(SearchCityModal(), handle_search)


def main() -> None:
    """Entry point for the application."""
    app = MovieShowtimesApp()
    app.run()


if __name__ == "__main__":
    main()
